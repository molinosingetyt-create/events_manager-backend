from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_notification import AppNotification
from app.models.employee import Employee
from app.models.enums import AppNotificationKind, EntityStatus
from app.models.overtime import OvertimeRequest
from app.models.permission import Permission
from app.models.profile import Profile, profile_permissions
from app.models.user import User


def _format_message(n: AppNotification) -> str:
    p = n.payload or {}
    if n.kind == AppNotificationKind.OVERTIME_PENDING.value:
        emp = p.get("employee_name") or "—"
        d = p.get("date") or "—"
        h = p.get("hours") or "—"
        return f"Nueva solicitud de horas extra pendiente: {emp} — {d} ({h} h)."
    if n.kind == AppNotificationKind.OVERTIME_DECIDED.value:
        emp = p.get("employee_name") or "—"
        d = p.get("date") or "—"
        decision = p.get("decision")
        verb = "aprobada" if decision == "approved" else "rechazada"
        return f"Su solicitud de horas extra del {d} para {emp} fue {verb}."
    return "Notificación"


async def notify_admins_new_pending_ot(
    db: AsyncSession,
    *,
    request_id: int,
    employee_name: str,
    request_date: str,
    hours: str,
    exclude_user_id: int | None = None,
) -> None:
    """Avisa a administración y gerencia por cada solicitud pendiente nueva."""
    r = await db.execute(
        select(User.id)
        .join(Profile, User.profile_id == Profile.id)
        .join(profile_permissions, profile_permissions.c.profile_id == Profile.id)
        .join(Permission, Permission.id == profile_permissions.c.permission_id)
        .where(Permission.code == "overtime.approve", User.status == EntityStatus.ACTIVE.value)
        .distinct()
    )
    kind = AppNotificationKind.OVERTIME_PENDING.value
    for (uid,) in r.all():
        if exclude_user_id is not None and uid == exclude_user_id:
            continue
        dup = await db.execute(
            select(AppNotification.id).where(
                AppNotification.user_id == uid,
                AppNotification.overtime_request_id == request_id,
                AppNotification.kind == kind,
            ).limit(1)
        )
        if dup.scalar_one_or_none() is not None:
            continue
        db.add(
            AppNotification(
                user_id=uid,
                kind=kind,
                overtime_request_id=request_id,
                payload={
                    "employee_name": employee_name,
                    "date": request_date,
                    "hours": hours,
                },
            )
        )


async def delete_pending_ot_for_request(db: AsyncSession, request_id: int) -> None:
    await db.execute(
        delete(AppNotification).where(
            AppNotification.overtime_request_id == request_id,
            AppNotification.kind == AppNotificationKind.OVERTIME_PENDING.value,
        )
    )


async def notify_requester_decision(
    db: AsyncSession,
    req: OvertimeRequest,
    *,
    approved: bool,
) -> None:
    """Notifica al usuario que creó la solicitud (p. ej. líder)."""
    kind = AppNotificationKind.OVERTIME_DECIDED.value
    dup = await db.execute(
        select(AppNotification.id).where(
            AppNotification.user_id == req.requested_by,
            AppNotification.overtime_request_id == req.id,
            AppNotification.kind == kind,
        ).limit(1)
    )
    if dup.scalar_one_or_none() is not None:
        return
    er = await db.execute(select(Employee.name).where(Employee.id == req.employee_id))
    emp_name = er.scalar_one_or_none() or "—"
    db.add(
        AppNotification(
            user_id=req.requested_by,
            kind=kind,
            overtime_request_id=req.id,
            payload={
                "employee_name": emp_name,
                "date": str(req.date),
                "hours": str(req.hours),
                "decision": "approved" if approved else "rejected",
            },
        )
    )


async def list_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    unread_only: bool = False,
    limit: int = 50,
) -> list[AppNotification]:
    q = select(AppNotification).where(AppNotification.user_id == user_id)
    if unread_only:
        q = q.where(AppNotification.read_at.is_(None))
    q = q.order_by(AppNotification.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return list(rows)


async def count_unread(db: AsyncSession, user_id: int) -> int:
    r = await db.execute(
        select(func.count())
        .select_from(AppNotification)
        .where(AppNotification.user_id == user_id, AppNotification.read_at.is_(None))
    )
    return int(r.scalar_one() or 0)


async def mark_read(db: AsyncSession, user_id: int, notification_id: int) -> AppNotification | None:
    r = await db.execute(
        select(AppNotification).where(
            AppNotification.id == notification_id,
            AppNotification.user_id == user_id,
        )
    )
    n = r.scalar_one_or_none()
    if not n:
        return None
    if n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
    await db.flush()
    return n


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    r = await db.execute(
        update(AppNotification)
        .where(AppNotification.user_id == user_id, AppNotification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    return r.rowcount  # type: ignore[union-attr]


def to_read_model(n: AppNotification) -> dict:
    return {
        "id": n.id,
        "kind": n.kind,
        "message": _format_message(n),
        "overtime_request_id": n.overtime_request_id,
        "read_at": n.read_at,
        "created_at": n.created_at,
        "payload": n.payload,
    }


