from fastapi import APIRouter

from app.api.v1 import areas, auth, employees, incapacity, notifications, overtime, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(areas.router, prefix="/areas", tags=["areas"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(overtime.router, prefix="/overtime-requests", tags=["overtime"])
api_router.include_router(incapacity.router, prefix="/incapacity-notes", tags=["incapacity"])
