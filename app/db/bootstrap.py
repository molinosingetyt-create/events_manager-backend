"""Creación de tablas y datos iniciales al arrancar la aplicación.

- Tablas: solo se ejecuta create_all si falta alguna tabla del modelo (idempotente).
- Seed: no inserta de nuevo el admin ni el área General si ya existen.

Nota: create_all no altera columnas en tablas ya existentes; migraciones de esquema
complejas siguen requiriendo Alembic.
"""

import logging
import os

from sqlalchemy import inspect, select

import app.models  # noqa: F401 — registra metadatos en Base
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models.area import Area
from app.models.enums import EntityStatus, Role
from app.models.user import User

logger = logging.getLogger(__name__)


def _all_model_tables_exist(sync_conn) -> bool:
    """True si la BD ya tiene todas las tablas declaradas en Base.metadata."""
    insp = inspect(sync_conn)
    existing = set(insp.get_table_names())
    needed = set(Base.metadata.tables.keys())
    return needed.issubset(existing)


async def init_db() -> None:
    async with engine.begin() as conn:
        present = await conn.run_sync(_all_model_tables_exist)
        if present:
            logger.info(
                "Esquema ya completo (%d tablas); no se ejecuta create_all.",
                len(Base.metadata.tables),
            )
            return
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tablas creadas o completadas (create_all).")


async def seed_admin() -> None:
    email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("ADMIN_PASSWORD", "Admin12345!")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            existing_user = await session.execute(
                select(User.id).where(User.email == email).limit(1)
            )
            if existing_user.scalar_one_or_none() is not None:
                logger.info(
                    "Seed omitido: el usuario admin ya existe (%s).",
                    email,
                )
                return

            r = await session.execute(select(Area).where(Area.name == "General"))
            area = r.scalar_one_or_none()
            if not area:
                area = Area(name="General", status=EntityStatus.ACTIVE.value)
                session.add(area)
                await session.flush()
                logger.info('Área "General" creada.')

            user = User(
                name="Administrator",
                email=email,
                hashed_password=get_password_hash(password),
                role=Role.ADMIN.value,
                area_id=area.id,
                status=EntityStatus.ACTIVE.value,
            )
            session.add(user)

        logger.info("Usuario admin creado: %s", email)
