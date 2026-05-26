"""[DEPRECATED] 대화별 llama-server 슬롯 고정.

기능이 upstream/instance_node.py의 InstanceSlotManager로 이전되었다.
이 모듈은 더 이상 openai_proxy.py에서 사용되지 않는다. 추후 제거 예정.
"""
from collections import OrderedDict

class SlotManager:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._conv_to_slot: OrderedDict[str, int] = OrderedDict()
        self._free: list[int] = list(range(capacity))

    def acquire(self, conv_id: str) -> int:
        """conv_id에 슬롯을 할당하거나 기존 슬롯을 반환한다."""
        if conv_id in self._conv_to_slot:
            self._conv_to_slot.move_to_end(conv_id)
            return self._conv_to_slot[conv_id]
        if self._free:
            slot_id = self._free.pop()
        else:
            _, slot_id = self._conv_to_slot.popitem(last=False)  # LRU 퇴거
        self._conv_to_slot[conv_id] = slot_id
        return slot_id

    def evict(self, conv_id: str) -> None:
        """conv_id의 슬롯을 명시적으로 해제한다 (대화 종료 시 호출 가능)."""
        if conv_id in self._conv_to_slot:
            slot_id = self._conv_to_slot.pop(conv_id)
            self._free.append(slot_id)


_manager: SlotManager | None = None


def get_slot_manager() -> SlotManager:  # pragma: no cover — deprecated, use Balancer instead
    raise RuntimeError(
        "get_slot_manager() is deprecated. Use apps.api.app.upstream.get_balancer() instead."
    )
