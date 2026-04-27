from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .errors import expired_api_key, invalid_api_key
from .models import ApiKey, User
from .security import decode_jwt, hash_api_key


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """JWT(대시보드) 인증."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    user_id = decode_jwt(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_api_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """API Key(OpenAI 프록시) 인증."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise invalid_api_key()
    plain = authorization.split(" ", 1)[1].strip()
    if not plain.startswith("sk-"):
        raise invalid_api_key()

    key = db.query(ApiKey).filter(ApiKey.key_hash == hash_api_key(plain)).one_or_none()
    if not key:
        raise invalid_api_key()
    if key.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise expired_api_key()

    user = db.get(User, key.user_id)
    if not user:
        raise invalid_api_key()
    return user
