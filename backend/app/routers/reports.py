from datetime import date

from fastapi import APIRouter, Depends, Query

from ..deps import active_user
from ..services import app_today, get_weekly_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/weekly")
def weekly(ref: date | None = Query(default=None, alias="date"), user=Depends(active_user)):
    return get_weekly_report(user["user_id"], ref or app_today())
