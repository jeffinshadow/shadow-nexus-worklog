from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import db
from ..deps import require_admin
from ..services import app_today, get_board, get_dashboard, get_weekly_report

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _ensure_user(user_id: int) -> None:
    if not db.query_one("SELECT 1 FROM users WHERE id = %s", (user_id,)):
        raise HTTPException(status_code=404, detail="usuario nao encontrado")


@router.get("/users")
def list_users(admin=Depends(require_admin)):
    return db.query_all(
        "SELECT id, email, role, created_at FROM users ORDER BY role DESC, email"
    )


@router.get("/users/{user_id}/board")
def user_board(user_id: int, admin=Depends(require_admin)):
    _ensure_user(user_id)
    return get_board(user_id)


@router.get("/users/{user_id}/dashboard")
def user_dashboard(user_id: int, admin=Depends(require_admin)):
    _ensure_user(user_id)
    return get_dashboard(user_id)


@router.get("/users/{user_id}/reports/weekly")
def user_report(
    user_id: int,
    ref: date | None = Query(default=None, alias="date"),
    admin=Depends(require_admin),
):
    _ensure_user(user_id)
    return get_weekly_report(user_id, ref or app_today())
