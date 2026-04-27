"""llama-server 네이티브 /completion 엔드포인트 클라이언트.

OpenAI messages 포맷 → ChatML prompt 변환, 네이티브 요청/응답을 OpenAI 포맷으로 변환한다.
slot_id와 cache_prompt를 통해 KV cache 재사용을 보장한다.
"""
import json
import time
import uuid

import httpx

from . import UpstreamConfig
from .client import make_client


# ---------------------------------------------------------------------------
# 포맷 변환
# ---------------------------------------------------------------------------

def messages_to_chatml(messages: list[dict]) -> str:
    """OpenAI messages 리스트를 ChatML prompt 문자열로 변환한다.

    어시스턴트 턴 오프너(<|im_start|>assistant\n)를 닫지 않고 끝내어
    llama-server가 그 지점에서 이어 생성하도록 한다.
    """
    parts: list[str] = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            content = "".join(
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            )
        parts.append(f"<|im_start|>{msg.get('role', 'user')}\n{content}<|im_end|>\n")
    parts.append("<|im_start|>assistant\n")
    return "".join(parts)


def build_native_request(body: dict, slot_id: int) -> dict:
    """OpenAI /v1/chat/completions 요청 body를 /completion 요청 body로 변환한다."""
    native: dict = {
        "prompt": messages_to_chatml(body.get("messages", [])),
        "slot_id": slot_id,
        "cache_prompt": True,
        "stream": bool(body.get("stream", False)),
    }
    if "max_tokens" in body:
        native["n_predict"] = body["max_tokens"]
    for key in (
        "temperature", "top_p", "top_k", "min_p", "repeat_penalty",
        "presence_penalty", "frequency_penalty", "seed", "stop",
    ):
        if key in body:
            native[key] = body[key]
    return native


def native_to_openai_response(native: dict, model: str) -> dict:
    """네이티브 /completion 응답을 OpenAI /v1/chat/completions 응답으로 변환한다.

    llama-server 버전에 따라 필드명이 다를 수 있으므로 두 이름을 모두 시도한다.
    (tokens_evaluated / prompt_tokens, tokens_predicted / predicted_n)
    """
    pt = int(native.get("tokens_evaluated") or native.get("prompt_tokens") or 0)
    ct = int(native.get("tokens_predicted") or native.get("predicted_n") or 0)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": native.get("content", "")},
                "finish_reason": "stop" if native.get("stop") else "length",
            }
        ],
        "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct},
    }


def native_chunk_to_sse(chunk: dict, cid: str, model: str) -> str:
    """네이티브 SSE 청크를 OpenAI SSE 라인으로 변환한다.

    stop=True인 마지막 청크에서 usage를 포함한 뒤 [DONE]을 붙인다.
    """
    if not chunk.get("stop"):
        obj = {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": {"content": chunk.get("content", "")}, "finish_reason": None}],
        }
        return f"data: {json.dumps(obj)}\n\n"

    pt = int(chunk.get("tokens_evaluated") or chunk.get("prompt_tokens") or 0)
    ct = int(chunk.get("tokens_predicted") or chunk.get("predicted_n") or 0)
    obj = {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct},
    }
    return f"data: {json.dumps(obj)}\n\ndata: [DONE]\n\n"


# ---------------------------------------------------------------------------
# HTTP 호출
# ---------------------------------------------------------------------------

async def call_native_non_stream(body: dict, slot_id: int, cfg: UpstreamConfig) -> dict:
    async with make_client(cfg) as client:
        try:
            r = await client.post("/completion", json=build_native_request(body, slot_id))
        except httpx.HTTPError as e:
            from ..errors import upstream_error
            raise upstream_error(f"Native completion error: {e}")
    return r.json()


async def call_native_stream(body: dict, slot_id: int, cfg: UpstreamConfig):
    """네이티브 /completion SSE 청크를 dict로 파싱해 yield한다."""
    async with make_client(cfg) as client:
        async with client.stream("POST", "/completion", json=build_native_request(body, slot_id)) as r:
            async for line in r.aiter_lines():
                if line.startswith("data: ") and (data := line[6:].strip()):
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        pass
