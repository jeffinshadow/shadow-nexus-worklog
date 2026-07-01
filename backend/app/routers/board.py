from fastapi import APIRouter, Depends

from ..deps import active_user
from ..services import get_board

router = APIRouter(prefix="/api/board", tags=["board"])


@router.get("")
def board(user=Depends(active_user)):
    return get_board(user["user_id"])
