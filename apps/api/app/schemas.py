from datetime import datetime

from pydantic import BaseModel


class CallbackRequest(BaseModel):
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    id: str
    email: str
    name: str
    usage_limit: int
    current_usage: int
    max_concurrent: int


class KeyInfo(BaseModel):
    prefix: str
    expires_at: datetime
    created_at: datetime


class IssuedKeyResponse(BaseModel):
    api_key: str  # 평문 — 1회 노출
    prefix: str
    expires_at: datetime


class UsageTodayResponse(BaseModel):
    used: int
    limit: int
    reset_at: datetime


class UsageHistoryItem(BaseModel):
    date: str
    total_tokens: int
    request_count: int
