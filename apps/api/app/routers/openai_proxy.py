"""OpenAI 호환 프록시.

지원: GET /v1/models, POST /v1/chat/completions (stream + non-stream).

미지원 엔드포인트(/v1/completions, /v1/embeddings)는 라우팅하지 않는다.
멀티 모델로 확장하려면 upstream/__init__.py의 UPSTREAMS dict에 항목을 추가하고,
chat_completions 핸들러는 이미 `resolve(model)`을 사용하므로 자동 라우팅된다.
"""
import asyncio
import json
import time
import uuid

import httpx
from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..concurrency import acquire_slot, release, try_acquire
from ..config import settings
from ..db import get_db
from ..deps import get_api_user
from ..errors import insufficient_quota, upstream_error
from ..models import RequestLog, User
from ..slot_manager import get_slot_manager
from ..upstream import resolve
from ..upstream.client import make_client
from ..upstream.llama_native import (
    call_native_non_stream,
    call_native_stream,
    native_chunk_to_sse,
    native_to_openai_response,
)
from ..upstream.token_count import count_messages, count_text

router = APIRouter(prefix="/v1", tags=["openai"])

# 클라이언트가 보낼 수 없는 서버 제어 필드 (덮어쓰거나 strip).
_SERVER_CONTROLLED = {"user"}


def _conv_id(user_id: str, x_conversation_id: str | None) -> str:
    """user_id로 스코핑된 대화 키를 반환한다.

    다른 사용자가 동일한 X-Conversation-ID를 보내도 슬롯이 겹치지 않도록
    user_id를 접두사로 붙인다.
    """
    cid = (x_conversation_id or "").strip() or "default"
    return f"{user_id}:{cid}"


def _quota_headers(user: User) -> dict[str, str]:
    remaining = max(0, user.usage_limit - user.current_usage)
    return {
        "X-RateLimit-Limit-Tokens": str(user.usage_limit),
        "X-RateLimit-Remaining-Tokens": str(remaining),
    }


def _log_and_charge(
    db: Session,
    user: User,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    status_code: int,
    latency_ms: int,
    ttft_ms: int | None,
) -> None:
    user.current_usage += prompt_tokens + completion_tokens
    db.add(
        RequestLog(
            user_id=user.id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status_code=status_code,
            latency_ms=latency_ms,
            ttft_ms=ttft_ms,
        )
    )
    db.commit()


@router.get("/models")
async def list_models(user: User = Depends(get_api_user)):
    """업스트림 /v1/models 응답을 그대로 프록시."""
    cfg = resolve(None)
    async with make_client(cfg) as client:
        try:
            r = await client.get("/v1/models")
        except httpx.HTTPError as e:
            raise upstream_error(f"Failed to reach upstream: {e}")
    return JSONResponse(
        status_code=r.status_code, content=r.json(), headers=_quota_headers(user)
    )


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    user: User = Depends(get_api_user),
    db: Session = Depends(get_db),
    x_conversation_id: str | None = Header(default=None),
):
    body = await request.json()
    model = body.get("model", "")
    messages = body.get("messages", [])
    is_stream = bool(body.get("stream", False))

    # 사전 quota 검사
    if user.current_usage >= user.usage_limit:
        raise insufficient_quota()

    # 서버 제어 필드 정리 + 스트리밍 usage 강제
    for k in _SERVER_CONTROLLED:
        body.pop(k, None)
    body["user"] = user.id
    if is_stream:
        opts = body.get("stream_options") or {}
        opts["include_usage"] = True
        body["stream_options"] = opts

    cfg = resolve(model)
    headers = _quota_headers(user)

    # 슬롯 고정 경로: LLAMA_SLOT_COUNT > 0일 때만 활성화
    if settings.LLAMA_SLOT_COUNT > 0:
        slot_id = get_slot_manager().acquire(_conv_id(user.id, x_conversation_id))
        if not is_stream:
            async with acquire_slot(user.id, user.max_concurrent):
                return await _do_native_non_stream(db, user, body, cfg, headers, slot_id)
        try_acquire(user.id, user.max_concurrent)
        try:
            return await _do_native_stream(db, user, body, messages, cfg, headers, slot_id)
        except BaseException:
            release(user.id)
            raise

    if not is_stream:
        async with acquire_slot(user.id, user.max_concurrent):
            return await _do_non_stream(db, user, body, cfg, headers)

    # 스트리밍은 response 반환 이후 generator가 실행되므로, async-with로 감싸면
    # 실제 스트림 도중 슬롯이 해제된다. 슬롯을 여기서 잡고 generator의 finally에서
    # 해제하도록 명시적으로 처리한다.
    try_acquire(user.id, user.max_concurrent)
    try:
        return await _do_stream(db, user, body, messages, cfg, headers)
    except BaseException:
        release(user.id)
        raise


async def _do_non_stream(
    db: Session, user: User, body: dict, cfg, headers: dict
) -> JSONResponse:
    started = time.perf_counter()
    async with make_client(cfg) as client:
        try:
            r = await client.post("/v1/chat/completions", json=body)
        except httpx.HTTPError as e:
            raise upstream_error(f"Upstream error: {e}")
    latency_ms = int((time.perf_counter() - started) * 1000)
    payload = r.json()

    usage = payload.get("usage") or {}
    pt = int(usage.get("prompt_tokens") or 0)
    ct = int(usage.get("completion_tokens") or 0)
    if pt == 0 and ct == 0:
        # 폴백: 최소한 prompt만 추정 (응답 본문 직렬화는 회피)
        pt = count_messages(body.get("messages", []))

    _log_and_charge(db, user, body.get("model", ""), pt, ct, r.status_code, latency_ms, None)

    out_headers = dict(headers)
    out_headers["X-RateLimit-Remaining-Tokens"] = str(max(0, user.usage_limit - user.current_usage))
    return JSONResponse(status_code=r.status_code, content=payload, headers=out_headers)


async def _do_stream(
    db: Session, user: User, body: dict, messages: list, cfg, headers: dict
) -> StreamingResponse:
    started = time.perf_counter()
    state = {
        "ttft_ms": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "local_completion_text": [],
        "got_upstream_usage": False,
    }

    async def gen():
        try:
            async with make_client(cfg) as client:
                async with client.stream("POST", "/v1/chat/completions", json=body) as r:
                    async for line in r.aiter_lines():
                        if state["ttft_ms"] is None and line.strip():
                            state["ttft_ms"] = int((time.perf_counter() - started) * 1000)
                        if line.startswith("data: "):
                            data = line[6:].strip()
                            if data and data != "[DONE]":
                                _absorb_chunk(state, data)
                        # SSE는 빈 줄 포함 그대로 전달
                        yield (line + "\n").encode("utf-8")
        except (asyncio.CancelledError, httpx.HTTPError):
            # 클라이언트 abort 또는 업스트림 오류 — 이미 받은 분만 차감
            pass
        finally:
            try:
                _finalize_stream(db, user, body, messages, state, started)
            finally:
                release(user.id)

    out_headers = dict(headers)
    out_headers["Content-Type"] = "text/event-stream"
    out_headers["Cache-Control"] = "no-cache"
    out_headers["Connection"] = "keep-alive"
    return StreamingResponse(gen(), media_type="text/event-stream", headers=out_headers)


def _absorb_chunk(state: dict, data: str) -> None:
    try:
        obj = json.loads(data)
    except json.JSONDecodeError:
        return
    usage = obj.get("usage")
    if usage:
        state["prompt_tokens"] = int(usage.get("prompt_tokens") or state["prompt_tokens"])
        state["completion_tokens"] = int(
            usage.get("completion_tokens") or state["completion_tokens"]
        )
        state["got_upstream_usage"] = True
    for choice in obj.get("choices") or []:
        delta = choice.get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            state["local_completion_text"].append(content)


def _finalize_stream(
    db: Session, user: User, body: dict, messages: list, state: dict, started: float
) -> None:
    latency_ms = int((time.perf_counter() - started) * 1000)
    if not state["got_upstream_usage"]:
        # 폴백: tiktoken으로 로컬 카운트
        state["prompt_tokens"] = count_messages(messages)
        state["completion_tokens"] = count_text("".join(state["local_completion_text"]))
    _log_and_charge(
        db,
        user,
        body.get("model", ""),
        state["prompt_tokens"],
        state["completion_tokens"],
        200,
        latency_ms,
        state["ttft_ms"],
    )


# ---------------------------------------------------------------------------
# 네이티브 /completion 경로 (LLAMA_SLOT_COUNT > 0)
# ---------------------------------------------------------------------------

async def _do_native_non_stream(
    db: Session, user: User, body: dict, cfg, headers: dict, slot_id: int
) -> JSONResponse:
    started = time.perf_counter()
    model = body.get("model", "")
    native = await call_native_non_stream(body, slot_id, cfg)
    latency_ms = int((time.perf_counter() - started) * 1000)
    resp = native_to_openai_response(native, model)
    u = resp["usage"]
    _log_and_charge(db, user, model, u["prompt_tokens"], u["completion_tokens"], 200, latency_ms, None)
    out = {**headers, "X-RateLimit-Remaining-Tokens": str(max(0, user.usage_limit - user.current_usage))}
    return JSONResponse(status_code=200, content=resp, headers=out)


async def _do_native_stream(
    db: Session, user: User, body: dict, messages: list, cfg, headers: dict, slot_id: int
) -> StreamingResponse:
    started = time.perf_counter()
    model = body.get("model", "")
    cid = f"chatcmpl-{uuid.uuid4().hex}"
    state = {"ttft_ms": None, "prompt_tokens": 0, "completion_tokens": 0}

    async def gen():
        try:
            async for chunk in call_native_stream(body, slot_id, cfg):
                if state["ttft_ms"] is None:
                    state["ttft_ms"] = int((time.perf_counter() - started) * 1000)
                if chunk.get("stop"):
                    state["prompt_tokens"] = int(
                        chunk.get("tokens_evaluated") or chunk.get("prompt_tokens") or 0
                    )
                    state["completion_tokens"] = int(
                        chunk.get("tokens_predicted") or chunk.get("predicted_n") or 0
                    )
                yield native_chunk_to_sse(chunk, cid, model).encode("utf-8")
        except (asyncio.CancelledError, httpx.HTTPError):
            pass
        finally:
            try:
                pt = state["prompt_tokens"] or count_messages(messages)
                ct = state["completion_tokens"]
                _log_and_charge(
                    db, user, model, pt, ct, 200,
                    int((time.perf_counter() - started) * 1000),
                    state["ttft_ms"],
                )
            finally:
                release(user.id)

    out_headers = dict(headers)
    out_headers["Content-Type"] = "text/event-stream"
    out_headers["Cache-Control"] = "no-cache"
    out_headers["Connection"] = "keep-alive"
    return StreamingResponse(gen(), media_type="text/event-stream", headers=out_headers)
