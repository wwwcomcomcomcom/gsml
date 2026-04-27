"""대화별 llama-server 슬롯 고정 (KV cache 재사용).

concurrency.py와 동일하게 단일 프로세스·asyncio 단일 스레드를 가정하므로 락이 없다.
SlotManager는 모듈 수준 싱글턴으로 관리된다.

슬롯이 부족하면 LRU(가장 오래전에 접근한) 대화를 퇴거시키고 그 슬롯을 재사용한다.
퇴거된 대화의 다음 요청은 새 슬롯을 받게 되어 llama-server가 캐시를 재구축한다.
"""
from collections import OrderedDict

from .config import settings


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


def get_slot_manager() -> SlotManager:
    global _manager
    if _manager is None:
        _manager = SlotManager(settings.LLAMA_SLOT_COUNT)
    return _manager
