"""Alertas y exportación del expediente HR (fase 5)."""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

AlertSeverity = Literal["info", "warning", "critical"]


class EmployeeProfileAlertRead(BaseModel):
    code: str
    severity: AlertSeverity
    title: str
    message: str
    due_date: Optional[date] = None


class EmployeeProfileAlertsBundleRead(BaseModel):
    employee_id: int
    employee_name: str
    identification_number: str
    alerts: list[EmployeeProfileAlertRead] = Field(default_factory=list)


class EmployeeProfileAlertsListRead(BaseModel):
    items: list[EmployeeProfileAlertsBundleRead] = Field(default_factory=list)
    total_alerts: int = 0
    employees_with_alerts: int = 0


class EmployeeProfileExportRowRead(BaseModel):
    employee_id: int
    identification_number: str
    name: str
    position: str
    area_name: str
    leader_name: Optional[str] = None
    status: str
    work_site_city: Optional[str] = None
    contract_type: Optional[str] = None
    contract_end_date: Optional[date] = None
    hire_date: Optional[date] = None
    collaborator_status: Optional[str] = None
    phone: Optional[str] = None
    corporate_email: Optional[str] = None
    personal_email: Optional[str] = None
    completeness_percent: int = 0
    active_alerts_count: int = 0
    documents_count: int = 0
    education_count: int = 0
    training_count: int = 0


class EmployeeProfileExportListRead(BaseModel):
    rows: list[EmployeeProfileExportRowRead] = Field(default_factory=list)
    generated_at: date
