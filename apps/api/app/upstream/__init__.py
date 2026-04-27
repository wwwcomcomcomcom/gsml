"""업스트림 LLM 라우팅 레지스트리.

현재는 단일 엔드포인트만 등록되어 있다. 멀티 모델 확장 지점:

    UPSTREAMS["llama3-70b"] = UpstreamConfig(base_url="http://other:8080")

그리고 openai_proxy.py에서 body["model"] 키로 라우팅하면 된다.
"""
from dataclasses import dataclass

from ..config import settings


@dataclass
class UpstreamConfig:
    base_url: str
    timeout: int = 600


# 현재는 단일 엔트리. dict 구조를 유지해 추후 추가만 하면 된다.
DEFAULT_UPSTREAM = UpstreamConfig(
    base_url=settings.UPSTREAM_BASE_URL.rstrip("/"),
    timeout=settings.UPSTREAM_TIMEOUT,
)

UPSTREAMS: dict[str, UpstreamConfig] = {}


def resolve(model_id: str | None) -> UpstreamConfig:
    """모델 ID로 업스트림을 선택. 등록되지 않은 모델은 기본 업스트림으로 폴백."""
    if model_id and model_id in UPSTREAMS:
        return UPSTREAMS[model_id]
    return DEFAULT_UPSTREAM
