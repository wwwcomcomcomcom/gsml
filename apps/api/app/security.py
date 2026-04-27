import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from .config import settings

ALGORITHM = "HS256"
KEY_BODY_LEN = 48
KEY_ALPHABET = string.ascii_letters + string.digits  # base62


def create_jwt(user_id: str) -> tuple[str, int]:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
    return token, settings.JWT_EXPIRE_HOURS * 3600


def decode_jwt(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def generate_api_key() -> str:
    body = "".join(secrets.choice(KEY_ALPHABET) for _ in range(KEY_BODY_LEN))
    return f"sk-{body}"


def hash_api_key(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def key_prefix(plain: str) -> str:
    # "sk-" + 첫 6자
    return plain[:9]
