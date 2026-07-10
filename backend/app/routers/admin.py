from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import db
from ..deps import require_admin
from ..services import get_board, get_dashboard
from .reports import build_pdf_response

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _ensure_user(user_id: int) -> dict:
    row = db.query_one("SELECT id, email FROM users WHERE id = %s", (user_id,))
    if not row:
        raise HTTPException(status_code=404, detail="usuario nao encontrado")
    return row


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


@router.get("/users/{user_id}/reports/export")
def user_report_export(
    user_id: int,
    start: date = Query(...),
    end: date = Query(...),
    admin=Depends(require_admin),
):
    target = _ensure_user(user_id)
    return build_pdf_response(target["email"], user_id, start, end)
