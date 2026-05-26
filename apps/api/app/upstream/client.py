"""httpx 기반 업스트림 호출 헬퍼."""
import httpx


def make_client(base_url: str, timeout: int = 600) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base_url, timeout=timeout)
