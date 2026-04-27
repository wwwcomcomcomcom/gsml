from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import ApiKey, User
from ..schemas import IssuedKeyResponse, KeyInfo
from ..security import generate_api_key, hash_api_key, key_prefix

router = APIRouter(prefix="/api/keys", tags=["keys"])


def _new_expires() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        days=settings.API_KEY_EXPIRE_DAYS
    )


@router.get("")
def get_key(user: User = Depends(get_current_user)) -> KeyInfo | None:
    if user.api_key is None:
        return None
    return KeyInfo(
        prefix=user.api_key.key_prefix,
        expires_at=user.api_key.expires_at,
        created_at=user.api_key.created_at,
    )


@router.post("", response_model=IssuedKeyResponse)
def issue_key(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> IssuedKeyResponse:
    if user.api_key is not None:
        raise HTTPException(status_code=409, detail="Key already exists. Use rotate.")
    plain = generate_api_key()
    record = ApiKey(
        user_id=user.id,
        key_hash=hash_api_key(plain),
        key_prefix=key_prefix(plain),
        expires_at=_new_expires(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return IssuedKeyResponse(api_key=plain, prefix=record.key_prefix, expires_at=record.expires_at)


@router.post("/rotate", response_model=IssuedKeyResponse)
def rotate_key(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> IssuedKeyResponse:
    if user.api_key is not None:
        db.delete(user.api_key)
        db.commit()
    plain = generate_api_key()
    record = ApiKey(
        user_id=user.id,
        key_hash=hash_api_key(plain),
        key_prefix=key_prefix(plain),
        expires_at=_new_expires(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return IssuedKeyResponse(api_key=plain, prefix=record.key_prefix, expires_at=record.expires_at)


@router.post("/extend", response_model=KeyInfo)
def extend_key(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> KeyInfo:
    if user.api_key is None:
        raise HTTPException(status_code=404, detail="No key to extend")
    user.api_key.expires_at = _new_expires()
    db.commit()
    db.refresh(user.api_key)
    return KeyInfo(
        prefix=user.api_key.key_prefix,
        expires_at=user.api_key.expires_at,
        created_at=user.api_key.created_at,
    )


@router.delete("", status_code=204)
def delete_key(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    if user.api_key is not None:
        db.delete(user.api_key)
        db.commit()
    return Response(status_code=204)
