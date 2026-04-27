"""토큰 카운팅 유틸.

업스트림이 usage를 돌려주면 그것을 우선 사용하고, 없으면 tiktoken으로 폴백.
모델별 인코딩 매핑이 정확하지 않을 수 있으므로 항상 cl100k_base를 사용 (근사치).
"""
from typing import Any

import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")


def count_text(text: str) -> int:
    return len(_ENC.encode(text or ""))


def count_messages(messages: list[dict[str, Any]]) -> int:
    """OpenAI chat 메시지의 prompt 토큰 근사치."""
    total = 0
    for m in messages:
        content = m.get("content")
        if isinstance(content, str):
            total += count_text(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += count_text(part.get("text", ""))
        # role 등 메타에 대해 메시지당 약 4 토큰 추가 (OpenAI 가이드)
        total += 4
    total += 2  # priming
    return total
