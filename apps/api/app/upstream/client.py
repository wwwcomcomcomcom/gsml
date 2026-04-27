"""httpx 기반 업스트림 호출 헬퍼."""
import httpx

from . import UpstreamConfig


def make_client(cfg: UpstreamConfig) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=cfg.base_url, timeout=cfg.timeout)
