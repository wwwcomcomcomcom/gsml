from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..models import User
from ..schemas import MeResponse

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=MeResponse)
def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        usage_limit=user.usage_limit,
        current_usage=user.current_usage,
        max_concurrent=user.max_concurrent,
    )
