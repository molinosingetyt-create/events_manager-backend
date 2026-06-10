"""Campos personalizados y nómina (fase 6)."""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field
import json

CustomFieldType = Literal["text", "number", "date", "boolean", "select", "textarea"]
PayrollConceptType = Literal[
    "salary",
    "bonus",
    "deduction",
    "transport",
    "overtime_pay",
    "social_security",
    "other",
]
PayrollSource = Literal["manual", "import", "system"]


class EmployeeCustomFieldDefRead(BaseModel):
    id: int
    field_key: str
    label: str
    field_type: CustomFieldType
    section: Optional[str] = None
    options: list[str] = Field(default_factory=list)
    is_required: bool = False
    sort_order: int = 0
    is_active: bool = True

    model_config = {"from_attributes": True}


class EmployeeCustomFieldDefCreate(BaseModel):
    field_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=255)
    field_type: CustomFieldType = "text"
    section: Optional[str] = Field(default=None, max_length=128)
    options: list[str] = Field(default_factory=list)
    is_required: bool = False
    sort_order: int = 0
    is_active: bool = True


class EmployeeCustomFieldDefUpdate(BaseModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=255)
    field_type: Optional[CustomFieldType] = None
    section: Optional[str] = Field(default=None, max_length=128)
    options: Optional[list[str]] = None
    is_required: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class EmployeeCustomFieldValueRead(BaseModel):
    field_def_id: int
    field_key: str
    label: str
    field_type: CustomFieldType
    section: Optional[str] = None
    options: list[str] = Field(default_factory=list)
    is_required: bool = False
    value: Optional[str] = None


class EmployeeCustomFieldValueWrite(BaseModel):
    field_key: str = Field(min_length=1, max_length=64)
    value: Optional[str] = None


class EmployeePayrollSummaryRead(BaseModel):
    base_salary: Optional[float] = None
    eps_name: Optional[str] = None
    eps_affiliation_number: Optional[str] = None
    pension_fund: Optional[str] = None
    severance_fund: Optional[str] = None
    family_compensation_box: Optional[str] = None
    arl_name: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_type: Optional[str] = None
    bank_account_number: Optional[str] = None
    notes: Optional[str] = None


class EmployeePayrollEntryRead(BaseModel):
    id: int
    period_month: date
    concept_type: PayrollConceptType
    description: str
    amount: Optional[float] = None
    reference_code: Optional[str] = None
    notes: Optional[str] = None
    source: PayrollSource
    created_by_name: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeePayrollEntryWrite(BaseModel):
    period_month: date
    concept_type: PayrollConceptType
    description: str = Field(min_length=1, max_length=255)
    amount: Optional[float] = Field(default=None, ge=-999999999, le=999999999)
    reference_code: Optional[str] = Field(default=None, max_length=64)
    notes: Optional[str] = None
    source: PayrollSource = "manual"


def options_from_json(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data]
    except json.JSONDecodeError:
        pass
    return []


def options_to_json(options: list[str]) -> Optional[str]:
    if not options:
        return None
    return json.dumps(options, ensure_ascii=False)
