from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import bad_request, not_found
from app.models.area import Area
from app.schemas.area import AreaCreate, AreaUpdate


async def get_area(db: AsyncSession, area_id: int) -> Area | None:
    r = await db.execute(select(Area).where(Area.id == area_id))
    return r.scalar_one_or_none()


async def list_areas(
    db: AsyncSession, *, page: int, page_size: int
) -> tuple[list[Area], int]:
    total = (await db.execute(select(func.count()).select_from(Area))).scalar_one()
    q = (
        select(Area).order_by(Area.id).offset((page - 1) * page_size).limit(page_size)
    )
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def create_area(db: AsyncSession, data: AreaCreate) -> Area:
    dup = await db.execute(select(Area).where(Area.name == data.name))
    if dup.scalar_one_or_none():
        raise bad_request("Ya existe un área con ese nombre")
    area = Area(name=data.name, status=data.status.value)
    db.add(area)
    await db.commit()
    await db.refresh(area)
    return area


async def update_area(db: AsyncSession, area_id: int, data: AreaUpdate) -> Area:
    area = await get_area(db, area_id)
    if not area:
        raise not_found("Área no encontrada")
    if data.name is not None:
        dup = await db.execute(
            select(Area).where(Area.name == data.name, Area.id != area_id)
        )
        if dup.scalar_one_or_none():
            raise bad_request("Ya existe un área con ese nombre")
        area.name = data.name
    if data.status is not None:
        area.status = data.status.value
    await db.commit()
    await db.refresh(area)
    return area


async def delete_area(db: AsyncSession, area_id: int) -> None:
    area = await get_area(db, area_id)
    if not area:
        raise not_found("Área no encontrada")
    from app.models.enums import EntityStatus

    area.status = EntityStatus.INACTIVE.value
    await db.commit()
