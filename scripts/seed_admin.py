"""Crea área General y usuario admin. También se ejecuta al arrancar la API."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.bootstrap import init_db, seed_admin


async def main() -> None:
    await init_db()
    await seed_admin()


if __name__ == "__main__":
    asyncio.run(main())
