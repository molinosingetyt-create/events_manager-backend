from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.employee_profile_phase6 import (
    EmployeeCustomFieldValueRead,
    EmployeeCustomFieldValueWrite,
    EmployeePayrollEntryRead,
    EmployeePayrollEntryWrite,
    EmployeePayrollSummaryRead,
)

DOCUMENT_KIND_LABELS: dict[str, str] = {
    "cedula": "Fotocopia cédula",
    "hoja_vida": "Hoja de vida",
    "soporte_academico": "Soporte académico",
    "certificacion_laboral": "Certificación laboral",
    "examen_ingreso": "Examen médico de ingreso",
    "contrato": "Contrato de trabajo firmado",
    "acta_induccion": "Acta de inducción",
    "confidencialidad": "Acuerdo de confidencialidad",
    "dotacion_epp": "Acta entrega dotación / EPP",
    "rut": "RUT",
    "certificacion_bancaria": "Certificación bancaria",
    "otro": "Otro documento",
}

DocumentKind = Literal[
    "cedula",
    "hoja_vida",
    "soporte_academico",
    "certificacion_laboral",
    "examen_ingreso",
    "contrato",
    "acta_induccion",
    "confidencialidad",
    "dotacion_epp",
    "rut",
    "certificacion_bancaria",
    "otro",
]
DocumentStatus = Literal["vigente", "vencido", "pendiente"]

DocumentType = Literal["CC", "CE", "PA", "TI", "NIT"]
LinkageType = Literal["direct", "temp_agency"]
WorkSiteCity = Literal["Barranquilla", "Bucaramanga", "Medellín", "Bogotá"]
HierarchicalLevel = Literal[
    "operario", "tecnico", "coordinador", "jefe", "director", "gerencia"
]
ContractType = Literal["fijo", "indefinido", "obra_labor", "aprendizaje"]
WorkModality = Literal["presencial", "remoto", "hibrido"]
CollaboratorStatus = Literal[
    "activo", "vacaciones", "incapacidad", "suspendido", "retirado"
]


class EmployeeDependentRead(BaseModel):
    id: int
    full_name: str
    relationship: Optional[str] = None
    birth_date: Optional[date] = None
    schooling: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeDependentWrite(BaseModel):
    id: Optional[int] = None
    full_name: str = Field(min_length=1, max_length=255)
    relationship: Optional[str] = Field(default=None, max_length=64)
    birth_date: Optional[date] = None
    schooling: Optional[str] = Field(default=None, max_length=128)


class EmployeePersonalRead(BaseModel):
    first_name: Optional[str] = None
    second_name: Optional[str] = None
    first_surname: Optional[str] = None
    second_surname: Optional[str] = None
    document_type: Optional[DocumentType] = None
    birth_date: Optional[date] = None
    age_years: Optional[int] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    children_count: Optional[int] = None
    residence_city: Optional[str] = None
    residence_address: Optional[str] = None
    neighborhood: Optional[str] = None
    phone: Optional[str] = None
    personal_email: Optional[str] = None
    corporate_email: Optional[str] = None
    photo_url: Optional[str] = None
    blood_type: Optional[str] = None
    rh_factor: Optional[str] = None


class EmployeePersonalUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, max_length=128)
    second_name: Optional[str] = Field(default=None, max_length=128)
    first_surname: Optional[str] = Field(default=None, max_length=128)
    second_surname: Optional[str] = Field(default=None, max_length=128)
    document_type: Optional[DocumentType] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=32)
    marital_status: Optional[str] = Field(default=None, max_length=32)
    children_count: Optional[int] = Field(default=None, ge=0, le=30)
    residence_city: Optional[str] = Field(default=None, max_length=128)
    residence_address: Optional[str] = Field(default=None, max_length=255)
    neighborhood: Optional[str] = Field(default=None, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=64)
    personal_email: Optional[str] = Field(default=None, max_length=255)
    corporate_email: Optional[str] = Field(default=None, max_length=255)
    blood_type: Optional[str] = Field(default=None, max_length=8)
    rh_factor: Optional[str] = Field(default=None, max_length=8)
    dependents: Optional[list[EmployeeDependentWrite]] = None


class EmployeeLaborRead(BaseModel):
    linkage_type: Optional[LinkageType] = None
    temp_agency_name: Optional[str] = None
    work_site_city: Optional[str] = None
    hierarchical_level: Optional[HierarchicalLevel] = None
    hire_date: Optional[date] = None
    seniority_text: Optional[str] = None
    contract_type: Optional[ContractType] = None
    contract_end_date: Optional[date] = None
    base_salary: Optional[Decimal] = None
    work_schedule_type: Optional[str] = None
    work_modality: Optional[WorkModality] = None
    eps_affiliation_number: Optional[str] = None
    eps_name: Optional[str] = None
    pension_fund: Optional[str] = None
    severance_fund: Optional[str] = None
    family_compensation_box: Optional[str] = None
    arl_name: Optional[str] = None
    arl_risk_level: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_type: Optional[str] = None
    bank_account_number: Optional[str] = None
    collaborator_status: Optional[CollaboratorStatus] = None
    notes: Optional[str] = None


class EmployeeLaborUpdate(BaseModel):
    linkage_type: Optional[LinkageType] = None
    temp_agency_name: Optional[str] = Field(default=None, max_length=255)
    work_site_city: Optional[str] = Field(default=None, max_length=128)
    hierarchical_level: Optional[HierarchicalLevel] = None
    hire_date: Optional[date] = None
    contract_type: Optional[ContractType] = None
    contract_end_date: Optional[date] = None
    base_salary: Optional[Decimal] = Field(default=None, ge=0)
    work_schedule_type: Optional[str] = Field(default=None, max_length=64)
    work_modality: Optional[WorkModality] = None
    eps_affiliation_number: Optional[str] = Field(default=None, max_length=64)
    eps_name: Optional[str] = Field(default=None, max_length=255)
    pension_fund: Optional[str] = Field(default=None, max_length=255)
    severance_fund: Optional[str] = Field(default=None, max_length=255)
    family_compensation_box: Optional[str] = Field(default=None, max_length=255)
    arl_name: Optional[str] = Field(default=None, max_length=255)
    arl_risk_level: Optional[str] = Field(default=None, max_length=32)
    bank_name: Optional[str] = Field(default=None, max_length=128)
    bank_account_type: Optional[str] = Field(default=None, max_length=32)
    bank_account_number: Optional[str] = Field(default=None, max_length=64)
    collaborator_status: Optional[CollaboratorStatus] = None
    notes: Optional[str] = None


class EmployeeProfileSummaryRead(BaseModel):
    id: int
    name: str
    identification_number: str
    position: str
    area_id: int
    area_name: str = ""
    temporal_category_name: str = ""
    leader_id: Optional[int] = None
    leader_name: Optional[str] = None
    status: str
    updated_at: datetime


class EmployeeDocumentRead(BaseModel):
    id: int
    employee_id: int
    document_kind: DocumentKind
    document_kind_label: str = ""
    display_name: str
    file_url: str
    content_type: str
    file_size: int = 0
    status: DocumentStatus
    expires_at: Optional[date] = None
    uploaded_by_id: Optional[int] = None
    uploaded_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EmployeeDocumentCreate(BaseModel):
    document_kind: DocumentKind
    display_name: Optional[str] = Field(default=None, max_length=255)
    status: DocumentStatus = "vigente"
    expires_at: Optional[date] = None


class EmployeeDocumentUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=255)
    status: Optional[DocumentStatus] = None
    expires_at: Optional[date] = None


class EmployeeFilterOptionsRead(BaseModel):
    areas: list[dict[str, int | str]] = Field(default_factory=list)
    leaders: list[dict[str, int | str]] = Field(default_factory=list)
    work_site_cities: list[str] = Field(default_factory=list)
    hierarchical_levels: list[str] = Field(default_factory=list)
    contract_types: list[str] = Field(default_factory=list)
    collaborator_statuses: list[str] = Field(default_factory=list)
    linkage_types: list[str] = Field(default_factory=list)
    document_kinds: list[dict[str, str]] = Field(default_factory=list)


EducationLevel = Literal[
    "primaria",
    "bachillerato",
    "tecnico",
    "tecnologo",
    "profesional",
    "especializacion",
    "maestria",
    "doctorado",
]
EducationStatus = Literal["culminado", "en_curso"]
TrainingType = Literal[
    "induccion",
    "tecnica",
    "seguridad",
    "soft_skills",
    "liderazgo",
    "normativa",
    "otro",
]


class EmployeeEducationRead(BaseModel):
    id: int
    education_level: Optional[EducationLevel] = None
    institution: Optional[str] = None
    program: Optional[str] = None
    graduation_year: Optional[int] = None
    status: Optional[EducationStatus] = None
    certificate_url: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeEducationWrite(BaseModel):
    education_level: Optional[EducationLevel] = None
    institution: Optional[str] = Field(default=None, max_length=255)
    program: Optional[str] = Field(default=None, max_length=255)
    graduation_year: Optional[int] = Field(default=None, ge=1950, le=2100)
    status: Optional[EducationStatus] = None
    certificate_url: Optional[str] = Field(default=None, max_length=512)


class EmployeeTrainingRead(BaseModel):
    id: int
    name: str
    provider: Optional[str] = None
    completed_at: Optional[date] = None
    hours: Optional[int] = None
    training_type: Optional[TrainingType] = None
    certificate_url: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeTrainingWrite(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider: Optional[str] = Field(default=None, max_length=255)
    completed_at: Optional[date] = None
    hours: Optional[int] = Field(default=None, ge=0, le=10000)
    training_type: Optional[TrainingType] = None
    certificate_url: Optional[str] = Field(default=None, max_length=512)


class EmployeePriorJobRead(BaseModel):
    id: int
    company_name: str
    position: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_text: Optional[str] = None
    economic_sector: Optional[str] = None
    leave_reason: Optional[str] = None
    reference_phone: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeePriorJobWrite(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    position: Optional[str] = Field(default=None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    economic_sector: Optional[str] = Field(default=None, max_length=128)
    leave_reason: Optional[str] = Field(default=None, max_length=255)
    reference_phone: Optional[str] = Field(default=None, max_length=64)


LanguageLevel = Literal["basico", "intermedio", "avanzado", "nativo"]
SoftwareProficiency = Literal["basico", "intermedio", "avanzado"]
WorkSstCertType = Literal[
    "altura",
    "espacios_confinados",
    "cargas",
    "electricos",
    "quimicos",
    "primeros_auxilios",
    "otro",
]
IncapacityOrigin = Literal["comun", "laboral", "maternidad", "paternidad", "otro"]
DisciplinaryActionType = Literal[
    "llamado_atencion",
    "acta_compromiso",
    "suspension",
    "otro",
]
AbsenceType = Literal["vacaciones", "permiso", "licencia", "ausencia", "otro"]


class EmployeeLanguageRead(BaseModel):
    id: int
    language: str
    level: Optional[LanguageLevel] = None

    model_config = {"from_attributes": True}


class EmployeeLanguageWrite(BaseModel):
    language: str = Field(min_length=1, max_length=64)
    level: Optional[LanguageLevel] = None


class EmployeeSoftwareSkillRead(BaseModel):
    id: int
    name: str
    proficiency: Optional[SoftwareProficiency] = None

    model_config = {"from_attributes": True}


class EmployeeSoftwareSkillWrite(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    proficiency: Optional[SoftwareProficiency] = None


class EmployeeDrivingLicenseRead(BaseModel):
    id: int
    category: str
    expires_at: Optional[date] = None

    model_config = {"from_attributes": True}


class EmployeeDrivingLicenseWrite(BaseModel):
    category: str = Field(min_length=1, max_length=16)
    expires_at: Optional[date] = None


class EmployeeWorkSstCertRead(BaseModel):
    id: int
    cert_type: WorkSstCertType
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    certificate_url: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeWorkSstCertWrite(BaseModel):
    cert_type: WorkSstCertType
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    certificate_url: Optional[str] = Field(default=None, max_length=512)


class EmployeeCompetencyEvaluationRead(BaseModel):
    id: int
    period_label: str
    rating: Optional[str] = None
    evaluator_name: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeCompetencyEvaluationWrite(BaseModel):
    period_label: str = Field(min_length=1, max_length=64)
    rating: Optional[str] = Field(default=None, max_length=64)
    evaluator_name: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class EmployeeSstProfileRead(BaseModel):
    entry_exam_date: Optional[date] = None
    entry_medical_concept: Optional[str] = None
    entry_restrictions: Optional[str] = None
    occupational_disease: Optional[str] = None
    current_medical_restrictions: Optional[str] = None


class EmployeeSstProfileUpdate(BaseModel):
    entry_exam_date: Optional[date] = None
    entry_medical_concept: Optional[str] = Field(default=None, max_length=255)
    entry_restrictions: Optional[str] = None
    occupational_disease: Optional[str] = None
    current_medical_restrictions: Optional[str] = None


class EmployeeSstPeriodicExamRead(BaseModel):
    id: int
    exam_date: Optional[date] = None
    result: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeSstPeriodicExamWrite(BaseModel):
    exam_date: Optional[date] = None
    result: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class EmployeeSstIncapacityRead(BaseModel):
    id: int
    origin: Optional[IncapacityOrigin] = None
    diagnosis: Optional[str] = None
    days: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    model_config = {"from_attributes": True}


class EmployeeSstIncapacityWrite(BaseModel):
    origin: Optional[IncapacityOrigin] = None
    diagnosis: Optional[str] = Field(default=None, max_length=255)
    days: Optional[int] = Field(default=None, ge=0, le=3650)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class EmployeeSstAccidentRead(BaseModel):
    id: int
    occurred_at: Optional[date] = None
    description: Optional[str] = None
    lost_days: Optional[int] = None

    model_config = {"from_attributes": True}


class EmployeeSstAccidentWrite(BaseModel):
    occurred_at: Optional[date] = None
    description: Optional[str] = None
    lost_days: Optional[int] = Field(default=None, ge=0, le=3650)


class EmployeeSstPpeRead(BaseModel):
    id: int
    item_name: str
    delivered_at: Optional[date] = None
    receipt_signed: bool = False

    model_config = {"from_attributes": True}


class EmployeeSstPpeWrite(BaseModel):
    item_name: str = Field(min_length=1, max_length=255)
    delivered_at: Optional[date] = None
    receipt_signed: bool = False


class EmployeeContractHistoryRead(BaseModel):
    id: int
    effective_date: Optional[date] = None
    contract_type: Optional[str] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeContractHistoryWrite(BaseModel):
    effective_date: Optional[date] = None
    contract_type: Optional[str] = Field(default=None, max_length=64)
    end_date: Optional[date] = None
    notes: Optional[str] = None


class EmployeeSalaryHistoryRead(BaseModel):
    id: int
    effective_date: Optional[date] = None
    previous_salary: Optional[float] = None
    new_salary: Optional[float] = None
    reason: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeSalaryHistoryWrite(BaseModel):
    effective_date: Optional[date] = None
    previous_salary: Optional[float] = Field(default=None, ge=0)
    new_salary: Optional[float] = Field(default=None, ge=0)
    reason: Optional[str] = Field(default=None, max_length=255)


class EmployeePerformanceReviewRead(BaseModel):
    id: int
    period_label: str
    rating: Optional[str] = None
    evaluator_name: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeePerformanceReviewWrite(BaseModel):
    period_label: str = Field(min_length=1, max_length=64)
    rating: Optional[str] = Field(default=None, max_length=64)
    evaluator_name: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class EmployeeRecognitionRead(BaseModel):
    id: int
    title: str
    recognized_at: Optional[date] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeRecognitionWrite(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    recognized_at: Optional[date] = None
    description: Optional[str] = None


class EmployeeDisciplinaryActionRead(BaseModel):
    id: int
    action_type: DisciplinaryActionType
    occurred_at: Optional[date] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeDisciplinaryActionWrite(BaseModel):
    action_type: DisciplinaryActionType
    occurred_at: Optional[date] = None
    description: Optional[str] = None


class EmployeeAbsenceRecordRead(BaseModel):
    id: int
    absence_type: AbsenceType
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: Optional[int] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class EmployeeAbsenceRecordWrite(BaseModel):
    absence_type: AbsenceType
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: Optional[int] = Field(default=None, ge=0, le=3650)
    notes: Optional[str] = None


class EmployeeProfileFullRead(BaseModel):
    employee: EmployeeProfileSummaryRead
    personal: EmployeePersonalRead
    labor: EmployeeLaborRead
    dependents: list[EmployeeDependentRead] = Field(default_factory=list)
    documents: list[EmployeeDocumentRead] = Field(default_factory=list)
    education: list[EmployeeEducationRead] = Field(default_factory=list)
    training: list[EmployeeTrainingRead] = Field(default_factory=list)
    prior_jobs: list[EmployeePriorJobRead] = Field(default_factory=list)
    languages: list[EmployeeLanguageRead] = Field(default_factory=list)
    software_skills: list[EmployeeSoftwareSkillRead] = Field(default_factory=list)
    driving_licenses: list[EmployeeDrivingLicenseRead] = Field(default_factory=list)
    work_sst_certs: list[EmployeeWorkSstCertRead] = Field(default_factory=list)
    competency_evaluations: list[EmployeeCompetencyEvaluationRead] = Field(default_factory=list)
    sst_profile: Optional[EmployeeSstProfileRead] = None
    sst_periodic_exams: list[EmployeeSstPeriodicExamRead] = Field(default_factory=list)
    sst_incapacities: list[EmployeeSstIncapacityRead] = Field(default_factory=list)
    sst_accidents: list[EmployeeSstAccidentRead] = Field(default_factory=list)
    sst_ppe: list[EmployeeSstPpeRead] = Field(default_factory=list)
    contract_history: list[EmployeeContractHistoryRead] = Field(default_factory=list)
    salary_history: list[EmployeeSalaryHistoryRead] = Field(default_factory=list)
    performance_reviews: list[EmployeePerformanceReviewRead] = Field(default_factory=list)
    recognitions: list[EmployeeRecognitionRead] = Field(default_factory=list)
    disciplinary_actions: list[EmployeeDisciplinaryActionRead] = Field(default_factory=list)
    absence_records: list[EmployeeAbsenceRecordRead] = Field(default_factory=list)
    custom_fields: list[EmployeeCustomFieldValueRead] = Field(default_factory=list)
    payroll_summary: Optional[EmployeePayrollSummaryRead] = None
    payroll_entries: list[EmployeePayrollEntryRead] = Field(default_factory=list)
    completeness_percent: int = 0
    can_edit: bool = False
    can_edit_documents: bool = False
    can_manage_custom_fields: bool = False
    can_edit_payroll: bool = False


class EmployeeProfilePatch(BaseModel):
    personal: Optional[EmployeePersonalUpdate] = None
    labor: Optional[EmployeeLaborUpdate] = None
    education: Optional[list[EmployeeEducationWrite]] = None
    training: Optional[list[EmployeeTrainingWrite]] = None
    prior_jobs: Optional[list[EmployeePriorJobWrite]] = None
    languages: Optional[list[EmployeeLanguageWrite]] = None
    software_skills: Optional[list[EmployeeSoftwareSkillWrite]] = None
    driving_licenses: Optional[list[EmployeeDrivingLicenseWrite]] = None
    work_sst_certs: Optional[list[EmployeeWorkSstCertWrite]] = None
    competency_evaluations: Optional[list[EmployeeCompetencyEvaluationWrite]] = None
    sst_profile: Optional[EmployeeSstProfileUpdate] = None
    sst_periodic_exams: Optional[list[EmployeeSstPeriodicExamWrite]] = None
    sst_incapacities: Optional[list[EmployeeSstIncapacityWrite]] = None
    sst_accidents: Optional[list[EmployeeSstAccidentWrite]] = None
    sst_ppe: Optional[list[EmployeeSstPpeWrite]] = None
    contract_history: Optional[list[EmployeeContractHistoryWrite]] = None
    salary_history: Optional[list[EmployeeSalaryHistoryWrite]] = None
    performance_reviews: Optional[list[EmployeePerformanceReviewWrite]] = None
    recognitions: Optional[list[EmployeeRecognitionWrite]] = None
    disciplinary_actions: Optional[list[EmployeeDisciplinaryActionWrite]] = None
    absence_records: Optional[list[EmployeeAbsenceRecordWrite]] = None
    custom_fields: Optional[list[EmployeeCustomFieldValueWrite]] = None
    payroll_entries: Optional[list[EmployeePayrollEntryWrite]] = None
