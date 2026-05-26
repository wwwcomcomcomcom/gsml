"""conv_id 기반 스티키 라우팅 + 슬롯 관리 + 헬스체크 루프."""
import asyncio
import logging
from typing import NamedTuple

from .instance_node import InstanceNode, InstanceStatus

logger = logging.getLogger(__name__)


class RouteEntry(NamedTuple):
    node: InstanceNode
    slot_id: int


class Balancer:
    """conv_id → (InstanceNode, slot_id) 매핑 관리.

    - 신규 conv: 가장 활성 conv가 적은 ALIVE 인스턴스 선정 (Least-Slots-Used)
    - 기존 conv: 동일 인스턴스 스티키
    - 인스턴스 DEAD 전환: 해당 conv들 다른 인스턴스로 재할당 (KV 캐시 리셋)
    - 전체 DEAD: RuntimeError → 호출부에서 503 변환
    - Idle 퇴거: 슬롯 만석 시 in-flight 없는 conv LRU 제거
    """

    def __init__(self, nodes: list[InstanceNode], hc_interval: int) -> None:
        self._nodes = nodes
        self._hc_interval = hc_interval
        # conv_id → RouteEntry
        self._routes: dict[str, RouteEntry] = {}
        # 현재 in-flight 요청 수 (conv_id → count)
        self._in_flight: dict[str, int] = {}
        self._hc_task: asyncio.Task | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        self._hc_task = asyncio.create_task(self._health_loop())

    async def stop(self) -> None:
        if self._hc_task:
            self._hc_task.cancel()
            try:
                await self._hc_task
            except asyncio.CancelledError:
                pass

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def alive_nodes(self) -> list[InstanceNode]:
        """현재 ALIVE 상태인 노드 목록."""
        return [n for n in self._nodes if n.is_alive]

    def acquire(self, conv_id: str) -> RouteEntry:
        """conv_id에 (InstanceNode, slot_id)를 할당하거나 기존 항목을 반환한다.

        ALIVE 인스턴스가 없으면 RuntimeError (호출부에서 503 변환).
        슬롯 만석이면 global Idle conv를 퇴거한 뒤 재시도.
        """
        # 기존 conv: 인스턴스가 살아있으면 그대로
        if conv_id in self._routes:
            entry = self._routes[conv_id]
            if entry.node.is_alive:
                self._mark_in_flight(conv_id)
                return entry
            # 인스턴스가 죽어있으면 재할당
            self._evict_conv(conv_id)

        node = self._pick_node()  # ALIVE 중 least-slots-used
        slot_id = self._acquire_slot(node, conv_id)
        entry = RouteEntry(node=node, slot_id=slot_id)
        self._routes[conv_id] = entry
        self._mark_in_flight(conv_id)
        return entry

    def release(self, conv_id: str) -> None:
        """요청 완료 시 in-flight 카운트 감소."""
        count = self._in_flight.get(conv_id, 1)
        if count <= 1:
            self._in_flight.pop(conv_id, None)
        else:
            self._in_flight[conv_id] = count - 1

    def evict_conv(self, conv_id: str) -> None:
        """외부에서 명시적으로 conv를 해제한다 (대화 종료 등)."""
        self._evict_conv(conv_id)

    # ── 내부 헬퍼 ──────────────────────────────────────────────────────────

    def _pick_node(self) -> InstanceNode:
        """ALIVE 인스턴스 중 active conv 수가 가장 적은 것을 반환."""
        alive = self.alive_nodes
        if not alive:
            raise RuntimeError("No alive upstream instances.")
        return min(alive, key=lambda n: n.slots.active_count)

    def _acquire_slot(self, node: InstanceNode, conv_id: str) -> int:
        """node에서 conv_id에 slot을 할당한다.

        free slot이 없으면 global Idle 퇴거 후 재시도.
        그래도 없으면 node 내부 LRU 퇴거 (경고 로그).
        """
        if node.slots.free_count == 0:
            self._evict_idle_global(node)
        if node.slots.free_count == 0:
            # 내부 LRU 퇴거 (모든 slot이 in-flight 중인 극단적 상황)
            victim = node.slots.lru_conv()
            if victim and victim in self._routes:
                logger.warning(
                    "Balancer: forced LRU eviction of conv=%s from instance=%s (all slots in-flight)",
                    victim,
                    node.url,
                )
                del self._routes[victim]
                self._in_flight.pop(victim, None)
        return node.slots.acquire(conv_id)

    def _evict_idle_global(self, prefer_node: InstanceNode | None = None) -> None:
        """in-flight 없는 conv 중 가장 오래된 것을 퇴거한다.

        prefer_node가 주어지면 해당 인스턴스의 conv를 우선 퇴거.
        """
        # prefer_node의 LRU idle 우선
        if prefer_node is not None:
            lru = prefer_node.slots.lru_conv()
            if lru and self._in_flight.get(lru, 0) == 0:
                logger.warning(
                    "Balancer: idle conv eviction conv=%s from instance=%s",
                    lru,
                    prefer_node.url,
                )
                self._evict_conv(lru)
                return

        # 전체 routes에서 idle conv LRU
        for conv_id, entry in list(self._routes.items()):
            if self._in_flight.get(conv_id, 0) == 0:
                logger.warning(
                    "Balancer: global idle conv eviction conv=%s from instance=%s",
                    conv_id,
                    entry.node.url,
                )
                self._evict_conv(conv_id)
                return

    def _evict_conv(self, conv_id: str) -> None:
        entry = self._routes.pop(conv_id, None)
        if entry:
            entry.node.slots.evict(conv_id)
        self._in_flight.pop(conv_id, None)

    def _mark_in_flight(self, conv_id: str) -> None:
        self._in_flight[conv_id] = self._in_flight.get(conv_id, 0) + 1

    # ── 헬스체크 루프 ──────────────────────────────────────────────────────

    async def _health_loop(self) -> None:
        while True:
            await asyncio.sleep(self._hc_interval)
            for node in self._nodes:
                ok = await node.check_health()
                if ok:
                    node.record_health_success()
                else:
                    became_dead = node.record_health_failure()
                    if became_dead:
                        self._failover_node(node)

    def _failover_node(self, dead_node: InstanceNode) -> None:
        """DEAD 인스턴스에 묶인 conv_id들을 모두 강제 해제.

        다음 acquire() 호출 시 다른 ALIVE 인스턴스로 재할당된다.
        KV 캐시는 포기.
        """
        victims = [cid for cid, e in list(self._routes.items()) if e.node is dead_node]
        if victims:
            logger.warning(
                "Balancer: failover — instance=%s DEAD, evicting %d convs: %s",
                dead_node.url,
                len(victims),
                victims,
            )
        for cid in victims:
            self._evict_conv(cid)
