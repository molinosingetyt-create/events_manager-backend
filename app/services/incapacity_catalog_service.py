from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import bad_request, not_found
from app.models.enums import EntityStatus, EpsArlKind
from app.models.incapacity_catalog import Diagnosis, EpsArlEntity, TemporalCategory
from app.schemas.incapacity_catalog import (
    DiagnosisCreate,
    DiagnosisRead,
    DiagnosisUpdate,
    EpsArlCreate,
    EpsArlRead,
    EpsArlUpdate,
    IncapacityFormOptionsRead,
    TemporalCategoryCreate,
    TemporalCategoryRead,
    TemporalCategoryUpdate,
)


async def _temporal_active(db: AsyncSession, temporal_id: int) -> TemporalCategory | None:
    r = await db.execute(
        select(TemporalCategory).where(
            TemporalCategory.id == temporal_id,
            TemporalCategory.status == EntityStatus.ACTIVE.value,
        )
    )
    return r.scalar_one_or_none()


async def require_active_temporal_category(db: AsyncSession, temporal_id: int) -> TemporalCategory:
    t = await _temporal_active(db, temporal_id)
    if not t:
        raise bad_request("Categoría temporal no válida o inactiva")
    return t


async def _eps_arl_active(db: AsyncSession, eps_arl_id: int) -> EpsArlEntity | None:
    r = await db.execute(
        select(EpsArlEntity).where(
            EpsArlEntity.id == eps_arl_id,
            EpsArlEntity.status == EntityStatus.ACTIVE.value,
        )
    )
    return r.scalar_one_or_none()


async def _diagnosis_active(db: AsyncSession, diagnosis_id: int) -> Diagnosis | None:
    r = await db.execute(
        select(Diagnosis).where(
            Diagnosis.id == diagnosis_id,
            Diagnosis.status == EntityStatus.ACTIVE.value,
        )
    )
    return r.scalar_one_or_none()


async def validate_note_catalog_refs(
    db: AsyncSession,
    *,
    temporal_category_id: int,
    eps_arl_id: int | None,
    diagnosis_id: int | None,
) -> None:
    t = await _temporal_active(db, temporal_category_id)
    if not t:
        raise bad_request("Categoría temporal no válida o inactiva")
    if eps_arl_id is not None:
        e = await _eps_arl_active(db, eps_arl_id)
        if not e:
            raise bad_request("EPS/ARL no válida o inactiva")
    if diagnosis_id is not None:
        d = await _diagnosis_active(db, diagnosis_id)
        if not d:
            raise bad_request("Diagnóstico no válido o inactivo")


# --- Temporal ---


async def list_temporal(
    db: AsyncSession, *, page: int, page_size: int, status: str | None
) -> tuple[list[TemporalCategory], int]:
    q = select(TemporalCategory)
    count_q = select(func.count()).select_from(TemporalCategory)
    if status:
        q = q.where(TemporalCategory.status == status)
        count_q = count_q.where(TemporalCategory.status == status)
    total = (await db.execute(count_q)).scalar_one()
    q = (
        q.order_by(TemporalCategory.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def get_temporal(db: AsyncSession, tid: int) -> TemporalCategory | None:
    r = await db.execute(select(TemporalCategory).where(TemporalCategory.id == tid))
    return r.scalar_one_or_none()


async def create_temporal(db: AsyncSession, data: TemporalCategoryCreate) -> TemporalCategory:
    dup = await db.execute(select(TemporalCategory).where(TemporalCategory.name == data.name))
    if dup.scalar_one_or_none():
        raise bad_request("Ya existe una categoría con ese nombre")
    row = TemporalCategory(name=data.name, status=data.status.value)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_temporal(db: AsyncSession, tid: int, data: TemporalCategoryUpdate) -> TemporalCategory:
    row = await get_temporal(db, tid)
    if not row:
        raise not_found("Categoría no encontrada")
    if data.name is not None:
        dup = await db.execute(
            select(TemporalCategory).where(
                TemporalCategory.name == data.name,
                TemporalCategory.id != tid,
            )
        )
        if dup.scalar_one_or_none():
            raise bad_request("Ya existe una categoría con ese nombre")
        row.name = data.name
    if data.status is not None:
        row.status = data.status.value
    await db.commit()
    await db.refresh(row)
    return row


async def delete_temporal(db: AsyncSession, tid: int) -> None:
    row = await get_temporal(db, tid)
    if not row:
        raise not_found("Categoría no encontrada")
    row.status = EntityStatus.INACTIVE.value
    await db.commit()


# --- EPS / ARL ---


async def list_eps_arl(
    db: AsyncSession, *, page: int, page_size: int, status: str | None, kind: str | None
) -> tuple[list[EpsArlEntity], int]:
    q = select(EpsArlEntity)
    count_q = select(func.count()).select_from(EpsArlEntity)
    if status:
        q = q.where(EpsArlEntity.status == status)
        count_q = count_q.where(EpsArlEntity.status == status)
    if kind:
        q = q.where(EpsArlEntity.kind == kind)
        count_q = count_q.where(EpsArlEntity.kind == kind)
    total = (await db.execute(count_q)).scalar_one()
    q = q.order_by(EpsArlEntity.kind, EpsArlEntity.name).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def get_eps_arl(db: AsyncSession, eid: int) -> EpsArlEntity | None:
    r = await db.execute(select(EpsArlEntity).where(EpsArlEntity.id == eid))
    return r.scalar_one_or_none()


async def create_eps_arl(db: AsyncSession, data: EpsArlCreate) -> EpsArlEntity:
    dup = await db.execute(
        select(EpsArlEntity).where(
            EpsArlEntity.kind == data.kind.value,
            EpsArlEntity.name == data.name,
        )
    )
    if dup.scalar_one_or_none():
        raise bad_request("Ya existe un registro con ese tipo y nombre")
    row = EpsArlEntity(
        kind=data.kind.value,
        name=data.name,
        code=(data.code.strip() if data.code and data.code.strip() else None),
        status=data.status.value,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_eps_arl(db: AsyncSession, eid: int, data: EpsArlUpdate) -> EpsArlEntity:
    row = await get_eps_arl(db, eid)
    if not row:
        raise not_found("Registro no encontrado")
    kind_val = data.kind.value if data.kind is not None else row.kind
    name_val = data.name if data.name is not None else row.name
    dup = await db.execute(
        select(EpsArlEntity).where(
            EpsArlEntity.kind == kind_val,
            EpsArlEntity.name == name_val,
            EpsArlEntity.id != eid,
        )
    )
    if dup.scalar_one_or_none():
        raise bad_request("Ya existe un registro con ese tipo y nombre")
    if data.kind is not None:
        row.kind = data.kind.value
    if data.name is not None:
        row.name = data.name
    if data.code is not None:
        row.code = data.code.strip() or None
    if data.status is not None:
        row.status = data.status.value
    await db.commit()
    await db.refresh(row)
    return row


async def delete_eps_arl(db: AsyncSession, eid: int) -> None:
    row = await get_eps_arl(db, eid)
    if not row:
        raise not_found("Registro no encontrado")
    row.status = EntityStatus.INACTIVE.value
    await db.commit()


# --- Diagnoses ---


async def list_diagnoses(
    db: AsyncSession, *, page: int, page_size: int, status: str | None
) -> tuple[list[Diagnosis], int]:
    q = select(Diagnosis)
    count_q = select(func.count()).select_from(Diagnosis)
    if status:
        q = q.where(Diagnosis.status == status)
        count_q = count_q.where(Diagnosis.status == status)
    total = (await db.execute(count_q)).scalar_one()
    q = q.order_by(Diagnosis.code).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def get_diagnosis(db: AsyncSession, did: int) -> Diagnosis | None:
    r = await db.execute(select(Diagnosis).where(Diagnosis.id == did))
    return r.scalar_one_or_none()


async def create_diagnosis(db: AsyncSession, data: DiagnosisCreate) -> Diagnosis:
    dup = await db.execute(select(Diagnosis).where(Diagnosis.code == data.code))
    if dup.scalar_one_or_none():
        raise bad_request("Ya existe un diagnóstico con ese código")
    row = Diagnosis(
        code=data.code.strip(),
        name=data.name.strip(),
        description=(data.description.strip() if data.description and data.description.strip() else None),
        status=data.status.value,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_diagnosis(db: AsyncSession, did: int, data: DiagnosisUpdate) -> Diagnosis:
    row = await get_diagnosis(db, did)
    if not row:
        raise not_found("Diagnóstico no encontrado")
    if data.code is not None:
        dup = await db.execute(
            select(Diagnosis).where(Diagnosis.code == data.code.strip(), Diagnosis.id != did)
        )
        if dup.scalar_one_or_none():
            raise bad_request("Ya existe un diagnóstico con ese código")
        row.code = data.code.strip()
    if data.name is not None:
        row.name = data.name.strip()
    if data.description is not None:
        row.description = data.description.strip() or None
    if data.status is not None:
        row.status = data.status.value
    await db.commit()
    await db.refresh(row)
    return row


async def delete_diagnosis(db: AsyncSession, did: int) -> None:
    row = await get_diagnosis(db, did)
    if not row:
        raise not_found("Diagnóstico no encontrado")
    row.status = EntityStatus.INACTIVE.value
    await db.commit()


def _eps_arl_label(e: EpsArlEntity) -> str:
    kind_es = "EPS" if e.kind == EpsArlKind.EPS.value else "ARL"
    return f"{kind_es} — {e.name}"


async def get_form_options(db: AsyncSession) -> IncapacityFormOptionsRead:
    tq = await db.execute(
        select(TemporalCategory)
        .where(TemporalCategory.status == EntityStatus.ACTIVE.value)
        .order_by(TemporalCategory.name)
    )
    eq = await db.execute(
        select(EpsArlEntity)
        .where(EpsArlEntity.status == EntityStatus.ACTIVE.value)
        .order_by(EpsArlEntity.kind, EpsArlEntity.name)
    )
    dq = await db.execute(
        select(Diagnosis)
        .where(Diagnosis.status == EntityStatus.ACTIVE.value)
        .order_by(Diagnosis.code)
    )
    temps = tq.scalars().all()
    eps = eq.scalars().all()
    diags = dq.scalars().all()
    return IncapacityFormOptionsRead(
        temporal_categories=[TemporalCategoryRead.model_validate(x) for x in temps],
        eps_arl=[EpsArlRead.model_validate(x) for x in eps],
        diagnoses=[DiagnosisRead.model_validate(x) for x in diags],
    )
