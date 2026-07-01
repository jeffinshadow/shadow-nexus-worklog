from fastapi import APIRouter, Depends

from ..deps import active_user
from ..services import get_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(user=Depends(active_user)):
    return get_dashboard(user["user_id"])
