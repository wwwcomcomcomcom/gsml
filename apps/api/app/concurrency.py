"""사용자별 동시 요청 제한.

프로세스 내 in-memory 카운터. 단일 프로세스·asyncio 단일 이벤트 루프 가정이므로
별도 락 없이 카운터 증감이 원자적이다.

멀티 워커가 필요해지면 Redis Lua counter로 교체 (apps/api/README.md 참조).
"""
from contextlib import asynccontextmanager

from .errors import rate_limited

_in_flight: dict[str, int] = {}


def try_acquire(user_id: str, limit: int) -> None:
    """한 슬롯을 점유. 한도 초과면 rate_limited()."""
    current = _in_flight.get(user_id, 0)
    if current >= limit:
        raise rate_limited()
    _in_flight[user_id] = current + 1


def release(user_id: str) -> None:
    _in_flight[user_id] = max(0, _in_flight.get(user_id, 1) - 1)


@asynccontextmanager
async def acquire_slot(user_id: str, limit: int):
    try_acquire(user_id, limit)
    try:
        yield
    finally:
        release(user_id)
