from fastapi import APIRouter

from app.api.v1 import (
    absenteeism,
    areas,
    auth,
    diagnoses,
    employees,
    org_chart,
    eps_arl,
    incapacity,
    notifications,
    overtime,
    rbac_admin,
    realtime_ws,
    shifts,
    temporal_categories,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(rbac_admin.router, prefix="/security", tags=["security"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(realtime_ws.router, prefix="/realtime", tags=["realtime"])
api_router.include_router(areas.router, prefix="/areas", tags=["areas"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(org_chart.router, prefix="/org-chart", tags=["org-chart"])
api_router.include_router(overtime.router, prefix="/overtime-requests", tags=["overtime"])
api_router.include_router(incapacity.router, prefix="/incapacity-notes", tags=["incapacity"])
api_router.include_router(absenteeism.router, prefix="/absenteeism-records", tags=["absenteeism"])
api_router.include_router(shifts.router, prefix="/shift-schedules", tags=["shifts"])
api_router.include_router(
    temporal_categories.router, prefix="/temporal-categories", tags=["incapacity-catalog"]
)
api_router.include_router(eps_arl.router, prefix="/eps-arl", tags=["incapacity-catalog"])
api_router.include_router(diagnoses.router, prefix="/diagnoses", tags=["incapacity-catalog"])
