"""웹 대시보드 전용 채팅 프록시.

JWT 인증만 허용하는 /api/chat/completions 엔드포인트.
API Key 없이 로그인된 사용자라면 누구나 /chat 페이지에서 채팅 가능.
사용량은 source="web" 으로 별도 집계된다.
"""
from fastapi import APIRouter, Depends, Header, Request

from ..concurrency import acquire_slot, release, try_acquire
from ..db import get_db
from ..deps import get_current_user
from ..errors import insufficient_quota, service_unavailable
from ..models import User
from ..upstream import get_balancer
from .openai_proxy import _conv_id, _do_native_non_stream, _do_native_stream, _quota_headers

from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/chat", tags=["web-chat"])

_SERVER_CONTROLLED = {"user"}


@router.post("/completions")
async def web_chat_completions(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_conversation_id: str | None = Header(default=None),
):
    body = await request.json()
    model = body.get("model", "")
    messages = body.get("messages", [])
    is_stream = bool(body.get("stream", False))

    if user.current_usage >= user.usage_limit:
        raise insufficient_quota()

    for k in _SERVER_CONTROLLED:
        body.pop(k, None)
    body["user"] = user.id
    if is_stream:
        opts = body.get("stream_options") or {}
        opts["include_usage"] = True
        body["stream_options"] = opts

    conv_id = _conv_id(user.id, x_conversation_id)
    headers = _quota_headers(user)

    try:
        route = get_balancer().acquire(conv_id)
    except RuntimeError:
        raise service_unavailable("No available inference instances.")

    if not is_stream:
        async with acquire_slot(user.id, user.max_concurrent):
            try:
                return await _do_native_non_stream(db, user, body, headers, route, source="web")
            finally:
                get_balancer().release(conv_id)

    try_acquire(user.id, user.max_concurrent)
    try:
        return await _do_native_stream(db, user, body, messages, headers, route, conv_id, source="web")
    except BaseException:
        release(user.id)
        get_balancer().release(conv_id)
        raise
