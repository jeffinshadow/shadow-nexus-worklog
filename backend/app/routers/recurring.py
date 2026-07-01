from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..deps import active_user_csrf
from ..schemas import RecurringIn, RecurringUpdate, ToggleIn
from ..services import app_today

router = APIRouter(prefix="/api/recurring", tags=["recurring"])


@router.post("", status_code=201)
def create(data: RecurringIn, user=Depends(active_user_csrf)):
    row = db.query_one(
        """
        INSERT INTO recurring_tasks (user_id, label, position)
        VALUES (%s, %s,
                (SELECT COALESCE(MAX(position), 0) + 1
                   FROM recurring_tasks WHERE user_id = %s))
        RETURNING id, label, position, active
        """,
        (user["user_id"], data.label, user["user_id"]),
    )
    return row


@router.patch("/{task_id}")
def update(task_id: int, data: RecurringUpdate, user=Depends(active_user_csrf)):
    fields, values = [], []
    if data.label is not None:
        fields.append("label = %s")
        values.append(data.label)
    if data.active is not None:
        fields.append("active = %s")
        values.append(data.active)
    if data.position is not None:
        fields.append("position = %s")
        values.append(data.position)
    if not fields:
        raise HTTPException(status_code=400, detail="nada para atualizar")

    values += [task_id, user["user_id"]]
    updated = db.execute(
        f"UPDATE recurring_tasks SET {', '.join(fields)} WHERE id = %s AND user_id = %s",
        tuple(values),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="nao encontrado")
    return {"ok": True}


@router.delete("/{task_id}")
def deactivate(task_id: int, user=Depends(active_user_csrf)):
    # Soft-delete: preserva o historico em recurring_completions.
    updated = db.execute(
        "UPDATE recurring_tasks SET active = false WHERE id = %s AND user_id = %s",
        (task_id, user["user_id"]),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="nao encontrado")
    return {"ok": True}


@router.post("/{task_id}/toggle")
def toggle(task_id: int, data: ToggleIn, user=Depends(active_user_csrf)):
    owns = db.query_one(
        "SELECT 1 FROM recurring_tasks WHERE id = %s AND user_id = %s",
        (task_id, user["user_id"]),
    )
    if not owns:
        raise HTTPException(status_code=404, detail="nao encontrado")

    today = app_today()
    if data.done:
        db.execute(
            """INSERT INTO recurring_completions (task_id, user_id, completed_date)
               VALUES (%s, %s, %s)
               ON CONFLICT (task_id, completed_date) DO NOTHING""",
            (task_id, user["user_id"], today),
        )
    else:
        db.execute(
            "DELETE FROM recurring_completions WHERE task_id = %s AND completed_date = %s",
            (task_id, today),
        )
    return {"ok": True, "done": data.done}
