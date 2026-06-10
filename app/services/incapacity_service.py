import json
from datetime import date, datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import bad_request, forbidden, not_found
from app.models.employee import Employee
from app.models.enums import EntityStatus, IncapacityHistoryAction, LongAbsenceDocumentKind, Role
from app.models.incapacity import IncapacityComment, IncapacityExtension, IncapacityNote, IncapacityNoteHistory
from app.models.profile import Profile
from app.models.user import User
from app.schemas.incapacity import IncapacityCommentCreate, IncapacityNoteCreate, IncapacityNoteUpdate
from app.services.employee_service import (
    acts_as_team_leader,
    ensure_employee_access,
    list_assignable_employees_for_actor,
)
from app.services.incapacity_catalog_service import (
    validate_note_catalog_refs,
)
from app.services.rbac_service import behavior_key, user_has_any_permission

_INC_BASE = (
    selectinload(IncapacityNote.employee),
    selectinload(IncapacityNote.creator),
    selectinload(IncapacityNote.temporal_category),
    selectinload(IncapacityNote.eps_arl),
    selectinload(IncapacityNote.diagnosis),
    selectinload(IncapacityNote.history_entries).selectinload(IncapacityNoteHistory.user),
)
_INC_LIST = _INC_BASE + (
    selectinload(IncapacityNote.extensions).selectinload(IncapacityExtension.creator),
)
_INC_FULL = _INC_BASE + (
    selectinload(IncapacityNote.comments).selectinload(IncapacityComment.user),
    selectinload(IncapacityNote.extensions).selectinload(IncapacityExtension.creator),
)


def inclusive_incapacity_days(start: date, end: date | None) -> int:
    """Días calendario inclusivos entre inicio y fin; sin fin cuenta como un solo día."""
    if end is None:
        return 1
    if end < start:
        raise bad_request("La fecha fin no puede ser anterior a la fecha de inicio")
    return (end - start).days + 1


def validate_long_absence_document_rules(*, start: date, end: date | None, kind: str | None) -> None:
    """Si la incapacidad es de 3+ días, debe indicarse historia clínica o incapacidad transcrita por EPS."""
    days = inclusive_incapacity_days(start, end)
    allowed = (
        LongAbsenceDocumentKind.HISTORIA_CLINICA.value,
        LongAbsenceDocumentKind.INCAPACIDAD_EPS.value,
    )
    if days >= 3:
        if kind not in allowed:
            raise bad_request(
                "Para incapacidades de 3 o más días debe indicar si el soporte es historia clínica "
                "o incapacidad transcrita por EPS."
            )
    elif kind is not None:
        raise bad_request(
            "El tipo de documento (historia clínica / EPS) solo aplica para incapacidades de 3 o más días."
        )


def validate_long_absence_supports(
    *,
    days: int,
    kind: str | None,
    second_file_url: str | None,
    eps_transcribed_text: str | None,
) -> None:
    """Historia clínica y EPS (3+ días): imagen opcional; no se admite texto transcrito."""
    txt = (eps_transcribed_text or "").strip()
    if days < 3:
        if second_file_url or txt:
            raise bad_request("El soporte adicional solo aplica para incapacidades de 3 o más días.")
        return
    if kind == LongAbsenceDocumentKind.HISTORIA_CLINICA.value and txt:
        raise bad_request(
            "No utilice texto transcrito; adjunte la imagen de historia clínica si corresponde."
        )
    if kind == LongAbsenceDocumentKind.INCAPACIDAD_EPS.value and txt:
        raise bad_request(
            "No utilice texto transcrito; adjunte la foto del documento de incapacidad EPS si corresponde."
        )


def _snapshot(note: IncapacityNote) -> str:
    return json.dumps(
        {
            "employee_id": note.employee_id,
            "type": note.type,
            "temporal_category_id": note.temporal_category_id,
            "eps_arl_id": note.eps_arl_id,
            "diagnosis_id": note.diagnosis_id,
            "description": note.description,
            "support": note.support,
            "start_date": str(note.start_date),
            "end_date": str(note.end_date) if note.end_date else None,
            "status": note.status,
            "file_url": note.file_url,
            "long_absence_document_kind": note.long_absence_document_kind,
            "long_absence_second_file_url": note.long_absence_second_file_url,
            "long_absence_eps_transcribed_text": note.long_absence_eps_transcribed_text,
        }
    )


async def _add_history(
    db: AsyncSession,
    incapacity_id: int,
    action: str,
    user_id: int | None,
    comment: str | None,
    snapshot: str | None,
) -> None:
    h = IncapacityNoteHistory(
        incapacity_id=incapacity_id,
        action=action,
        user_id=user_id,
        comment=comment,
        snapshot=snapshot,
        created_at=datetime.now(timezone.utc),
    )
    db.add(h)


async def list_leader_filter_options(db: AsyncSession) -> list[tuple[int, str]]:
    """Usuarios activos con comportamiento o rol de líder."""
    r = await db.execute(
        select(User.id, User.name)
        .join(Profile, User.profile_id == Profile.id)
        .where(
            User.status == EntityStatus.ACTIVE.value,
            or_(Profile.behavior_key == Role.LEADER.value, User.role == Role.LEADER.value),
        )
        .order_by(User.name.asc(), User.id.asc())
    )
    return [(row[0], row[1]) for row in r.all()]


async def list_assignable_employees(
    db: AsyncSession,
    actor: User,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
) -> tuple[list[Employee], int]:
    return await list_assignable_employees_for_actor(
        db, actor, page=page, page_size=page_size, search=search
    )


async def get_note(db: AsyncSession, note_id: int) -> IncapacityNote | None:
    r = await db.execute(
        select(IncapacityNote)
        .options(*_INC_FULL)
        .where(IncapacityNote.id == note_id)
    )
    return r.scalar_one_or_none()


async def list_notes(
    db: AsyncSession,
    actor: User,
    *,
    page: int,
    page_size: int,
    employee_id: int | None = None,
    type_filter: str | None = None,
    search: str | None = None,
    leader_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    has_extension: bool | None = None,
) -> tuple[list[IncapacityNote], int]:
    q = select(IncapacityNote)
    count_q = select(func.count()).select_from(IncapacityNote)

    emp_join_needed = (
        bool(search and search.strip())
        or leader_id is not None
        or acts_as_team_leader(actor)
    )
    if emp_join_needed:
        q = q.join(Employee, IncapacityNote.employee_id == Employee.id)
        count_q = count_q.join(Employee, IncapacityNote.employee_id == Employee.id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        emp_cond = or_(Employee.name.ilike(term), Employee.identification_number.ilike(term))
        q = q.where(emp_cond)
        count_q = count_q.where(emp_cond)

    if acts_as_team_leader(actor):
        q = q.where(Employee.leader_id == actor.id)
        count_q = count_q.where(Employee.leader_id == actor.id)
    elif leader_id is not None:
        q = q.where(Employee.leader_id == leader_id)
        count_q = count_q.where(Employee.leader_id == leader_id)

    if employee_id is not None:
        q = q.where(IncapacityNote.employee_id == employee_id)
        count_q = count_q.where(IncapacityNote.employee_id == employee_id)
    if type_filter:
        q = q.where(IncapacityNote.type == type_filter)
        count_q = count_q.where(IncapacityNote.type == type_filter)
    if date_from is not None:
        overlap_from = or_(IncapacityNote.end_date.is_(None), IncapacityNote.end_date >= date_from)
        q = q.where(overlap_from)
        count_q = count_q.where(overlap_from)
    if date_to is not None:
        q = q.where(IncapacityNote.start_date <= date_to)
        count_q = count_q.where(IncapacityNote.start_date <= date_to)

    if has_extension is not None:
        ext_exists = (
            select(IncapacityExtension.id)
            .where(IncapacityExtension.incapacity_id == IncapacityNote.id)
            .exists()
        )
        if has_extension:
            q = q.where(ext_exists)
            count_q = count_q.where(ext_exists)
        else:
            q = q.where(~ext_exists)
            count_q = count_q.where(~ext_exists)

    total = (await db.execute(count_q)).scalar_one()
    q = (
        q.order_by(IncapacityNote.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .options(*_INC_LIST)
    )
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def ensure_employee_scope(db: AsyncSession, actor: User, employee_id: int) -> Employee:
    er = await db.execute(select(Employee).where(Employee.id == employee_id))
    emp = er.scalar_one_or_none()
    if not emp:
        raise bad_request("Empleado no encontrado")
    if acts_as_team_leader(actor):
        ensure_employee_access(actor, emp)
    return emp


async def create_note(
    db: AsyncSession,
    actor: User,
    data: IncapacityNoteCreate,
    file_url: str | None,
    *,
    long_absence_second_file_url: str | None = None,
) -> IncapacityNote:
    if acts_as_team_leader(actor):
        await ensure_employee_scope(db, actor, data.employee_id)
    elif behavior_key(actor) in (Role.ADMIN.value, Role.HR.value, Role.MANAGEMENT.value):
        er = await db.execute(select(Employee).where(Employee.id == data.employee_id))
        if not er.scalar_one_or_none():
            raise bad_request("Empleado no encontrado")
    else:
        raise forbidden("No tiene permiso para crear este registro")

    await validate_note_catalog_refs(
        db,
        temporal_category_id=data.temporal_category_id,
        eps_arl_id=data.eps_arl_id,
        diagnosis_id=data.diagnosis_id,
    )

    kind_val = data.long_absence_document_kind.value if data.long_absence_document_kind else None
    validate_long_absence_document_rules(
        start=data.start_date,
        end=data.end_date,
        kind=kind_val,
    )

    days = inclusive_incapacity_days(data.start_date, data.end_date)
    validate_long_absence_supports(
        days=days,
        kind=kind_val,
        second_file_url=long_absence_second_file_url,
        eps_transcribed_text=None,
    )

    # Quien tenga incapacity.approve puede dejar el estado indicado; el resto queda pendiente.
    if await user_has_any_permission(db, actor, "incapacity.approve"):
        status_val = data.status.value
    else:
        status_val = EntityStatus.PENDING.value

    note = IncapacityNote(
        employee_id=data.employee_id,
        type=data.type.value,
        temporal_category_id=data.temporal_category_id,
        eps_arl_id=data.eps_arl_id,
        diagnosis_id=data.diagnosis_id,
        description=(data.description.strip() if data.description and data.description.strip() else None),
        support=(data.support.strip() if data.support and data.support.strip() else None),
        start_date=data.start_date,
        end_date=data.end_date,
        causation_year=data.causation_year,
        causation_month=data.causation_month,
        causation_half=data.causation_half,
        long_absence_document_kind=kind_val,
        long_absence_second_file_url=long_absence_second_file_url,
        long_absence_eps_transcribed_text=None,
        file_url=file_url,
        created_by=actor.id,
        status=status_val,
    )
    db.add(note)
    await db.flush()
    await _add_history(
        db,
        note.id,
        IncapacityHistoryAction.CREATED.value,
        actor.id,
        None,
        _snapshot(note),
    )
    await db.commit()
    r2 = await db.execute(select(IncapacityNote).options(*_INC_FULL).where(IncapacityNote.id == note.id))
    return r2.scalar_one()


async def update_note(
    db: AsyncSession, actor: User, note_id: int, data: IncapacityNoteUpdate, file_url: str | None
) -> IncapacityNote:
    note = await get_note(db, note_id)
    if not note:
        raise not_found("Registro no encontrado")

    emp = await ensure_employee_scope_for_read(db, actor, note)

    if not can_modify_note(actor, note, emp):
        raise forbidden("No puede modificar este registro")

    old_status = note.status

    if data.type is not None:
        note.type = data.type.value
    if data.description is not None:
        note.description = data.description.strip() or None
    if data.support is not None:
        note.support = data.support.strip() or None
    if data.start_date is not None:
        note.start_date = data.start_date
    if data.end_date is not None:
        note.end_date = data.end_date
    if "causation_year" in data.model_fields_set:
        note.causation_year = data.causation_year
    if "causation_month" in data.model_fields_set:
        note.causation_month = data.causation_month
    if "causation_half" in data.model_fields_set:
        note.causation_half = data.causation_half
    if "temporal_category_id" in data.model_fields_set:
        if data.temporal_category_id is None:
            raise bad_request("La categoría temporal es obligatoria")
        note.temporal_category_id = data.temporal_category_id
    if "eps_arl_id" in data.model_fields_set:
        note.eps_arl_id = data.eps_arl_id
    if "diagnosis_id" in data.model_fields_set:
        note.diagnosis_id = data.diagnosis_id
    if "long_absence_document_kind" in data.model_fields_set:
        note.long_absence_document_kind = (
            data.long_absence_document_kind.value if data.long_absence_document_kind else None
        )

    await validate_note_catalog_refs(
        db,
        temporal_category_id=note.temporal_category_id,
        eps_arl_id=note.eps_arl_id,
        diagnosis_id=note.diagnosis_id,
    )

    validate_long_absence_document_rules(
        start=note.start_date,
        end=note.end_date,
        kind=note.long_absence_document_kind,
    )

    if data.status is not None:
        new_s = data.status.value
        if new_s in (EntityStatus.APPROVED.value, EntityStatus.REJECTED.value):
            if not await user_has_any_permission(db, actor, "incapacity.approve"):
                raise forbidden("No tiene permiso para aprobar o rechazar incapacidades")
            if note.status != EntityStatus.PENDING.value:
                raise bad_request("Solo se pueden aprobar o rechazar registros pendientes")
        note.status = new_s
    if file_url is not None:
        note.file_url = file_url

    decision = (
        data.status is not None
        and old_status == EntityStatus.PENDING.value
        and note.status in (EntityStatus.APPROVED.value, EntityStatus.REJECTED.value)
    )
    if decision:
        action = (
            IncapacityHistoryAction.APPROVED.value
            if note.status == EntityStatus.APPROVED.value
            else IncapacityHistoryAction.REJECTED.value
        )
        await _add_history(db, note_id, action, actor.id, None, _snapshot(note))
    elif (
        file_url is not None
        or data.type is not None
        or data.description is not None
        or data.support is not None
        or data.start_date is not None
        or data.end_date is not None
        or "temporal_category_id" in data.model_fields_set
        or "eps_arl_id" in data.model_fields_set
        or "diagnosis_id" in data.model_fields_set
        or "long_absence_document_kind" in data.model_fields_set
        or (data.status is not None and not decision)
    ):
        comment = "Se adjuntó un archivo" if file_url is not None and not any(
            [
                data.type is not None,
                data.description is not None,
                data.support is not None,
                data.start_date is not None,
                data.end_date is not None,
                data.status is not None,
                "temporal_category_id" in data.model_fields_set,
                "eps_arl_id" in data.model_fields_set,
                "diagnosis_id" in data.model_fields_set,
                "long_absence_document_kind" in data.model_fields_set,
            ]
        ) else None
        await _add_history(
            db,
            note_id,
            IncapacityHistoryAction.UPDATED.value,
            actor.id,
            comment or "Registro actualizado",
            _snapshot(note),
        )

    await db.commit()
    r2 = await db.execute(select(IncapacityNote).options(*_INC_FULL).where(IncapacityNote.id == note_id))
    return r2.scalar_one()


async def ensure_employee_scope_for_read(
    db: AsyncSession, actor: User, note: IncapacityNote
) -> Employee:
    er = await db.execute(select(Employee).where(Employee.id == note.employee_id))
    emp = er.scalar_one_or_none()
    if not emp:
        raise not_found("Empleado no encontrado")
    if acts_as_team_leader(actor):
        ensure_employee_access(actor, emp)
    return emp


def can_modify_note(actor: User, note: IncapacityNote, emp: Employee) -> bool:
    if behavior_key(actor) in (Role.ADMIN.value, Role.HR.value):
        return True
    if acts_as_team_leader(actor):
        return emp.leader_id == actor.id and note.created_by == actor.id
    if behavior_key(actor) == Role.MANAGEMENT.value:
        return True
    return False


async def create_extension(
    db: AsyncSession,
    actor: User,
    note_id: int,
    *,
    start_date: date,
    end_date: date,
    file_url: str | None,
    note_text: str | None,
) -> IncapacityExtension:
    note = await get_note(db, note_id)
    if not note:
        raise not_found("Registro no encontrado")
    await ensure_employee_scope_for_read(db, actor, note)
    if end_date < start_date:
        raise bad_request("La fecha fin no puede ser anterior a la fecha de inicio.")
    incap_fin = note.end_date if note.end_date is not None else note.start_date
    if start_date < incap_fin:
        raise bad_request(
            "La fecha de inicio de la prórroga debe ser igual o posterior a la fecha fin de la incapacidad."
        )
    if end_date < incap_fin:
        raise bad_request(
            "La fecha fin de la prórroga debe ser igual o posterior a la fecha fin de la incapacidad."
        )

    note_clean = (note_text or "").strip() or None
    ext = IncapacityExtension(
        incapacity_id=note_id,
        start_date=start_date,
        end_date=end_date,
        file_url=file_url,
        note=note_clean,
        created_by=actor.id,
    )
    db.add(ext)
    await db.flush()
    snap = json.dumps(
        {
            "extension_id": ext.id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "note": note_clean,
            "file_url": file_url,
        },
        ensure_ascii=False,
    )
    await _add_history(
        db,
        note_id,
        IncapacityHistoryAction.EXTENSION_ADDED.value,
        actor.id,
        f"Prórroga registrada ({start_date} → {end_date})",
        snap,
    )
    await db.refresh(ext)
    return ext


async def add_comment(
    db: AsyncSession, actor: User, note_id: int, data: IncapacityCommentCreate
) -> IncapacityComment:
    note = await get_note(db, note_id)
    if not note:
        raise not_found("Registro no encontrado")
    await ensure_employee_scope_for_read(db, actor, note)

    c = IncapacityComment(
        incapacity_id=note_id,
        user_id=actor.id,
        comment=data.comment,
        created_at=datetime.now(timezone.utc),
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def delete_note(db: AsyncSession, actor: User, note_id: int) -> None:
    note = await get_note(db, note_id)
    if not note:
        raise not_found("Registro no encontrado")
    emp = await ensure_employee_scope_for_read(db, actor, note)
    if not can_modify_note(actor, note, emp):
        raise forbidden("No puede eliminar este registro")
    await db.execute(delete(IncapacityNote).where(IncapacityNote.id == note_id))
    await db.commit()
