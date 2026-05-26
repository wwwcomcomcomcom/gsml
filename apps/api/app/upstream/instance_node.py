"""단일 llama-server 인스턴스 노드: 상태 추적 + 슬롯 관리."""
import logging
from collections import OrderedDict
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class InstanceStatus(Enum):
    ALIVE = "ALIVE"
    DEAD = "DEAD"


class InstanceSlotManager:
    """단일 인스턴스의 conv_id → slot_id 매핑 + LRU 퇴거.

    슬롯이 모자라면 Balancer가 먼저 global Idle 퇴거를 시도한다.
    그래도 모자라면 내부 LRU 퇴거를 한다 (경고 로그는 Balancer 측에서 찍음).
    """

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._conv_to_slot: OrderedDict[str, int] = OrderedDict()
        self._free: list[int] = list(range(capacity))

    @property
    def active_count(self) -> int:
        return len(self._conv_to_slot)

    @property
    def free_count(self) -> int:
        return len(self._free)

    def acquire(self, conv_id: str) -> int:
        """conv_id에 slot 할당. 기존이면 같은 slot 반환 (LRU 갱신)."""
        if conv_id in self._conv_to_slot:
            self._conv_to_slot.move_to_end(conv_id)
            return self._conv_to_slot[conv_id]
        if self._free:
            slot_id = self._free.pop()
        else:
            # LRU 퇴거 (Balancer 레벨 Idle 퇴거로 여기까지 안 오는 게 정상)
            _, slot_id = self._conv_to_slot.popitem(last=False)
        self._conv_to_slot[conv_id] = slot_id
        return slot_id

    def evict(self, conv_id: str) -> None:
        if conv_id in self._conv_to_slot:
            slot_id = self._conv_to_slot.pop(conv_id)
            self._free.append(slot_id)

    def has(self, conv_id: str) -> bool:
        return conv_id in self._conv_to_slot

    def lru_conv(self) -> str | None:
        """LRU conv_id 반환 (가장 오래된 것). 없으면 None."""
        if self._conv_to_slot:
            return next(iter(self._conv_to_slot))
        return None


class InstanceNode:
    """llama-server 단일 인스턴스 노드.

    헬스체크 상태(ALIVE/DEAD)와 슬롯 매핑을 함께 관리한다.
    """

    def __init__(self, url: str, slot_count: int, fail_threshold: int) -> None:
        self.url = url
        self.slot_count = slot_count
        self._fail_threshold = fail_threshold
        self._status = InstanceStatus.ALIVE
        self._consecutive_failures = 0
        self.slots = InstanceSlotManager(slot_count)

    @property
    def status(self) -> InstanceStatus:
        return self._status

    @property
    def is_alive(self) -> bool:
        return self._status == InstanceStatus.ALIVE

    def record_health_success(self) -> None:
        was_dead = self._status == InstanceStatus.DEAD
        self._consecutive_failures = 0
        self._status = InstanceStatus.ALIVE
        if was_dead:
            logger.info("Instance %s recovered: DEAD → ALIVE", self.url)

    def record_health_failure(self) -> bool:
        """실패 기록. 이번 호출로 DEAD로 전환되면 True 반환."""
        self._consecutive_failures += 1
        if (
            self._consecutive_failures >= self._fail_threshold
            and self._status == InstanceStatus.ALIVE
        ):
            self._status = InstanceStatus.DEAD
            logger.info(
                "Instance %s went DEAD after %d consecutive failures",
                self.url,
                self._consecutive_failures,
            )
            return True
        return False

    async def check_health(self, timeout: float = 5.0) -> bool:
        try:
            async with httpx.AsyncClient(base_url=self.url, timeout=timeout) as client:
                r = await client.get("/health")
                return r.status_code == 200
        except Exception:
            return False
