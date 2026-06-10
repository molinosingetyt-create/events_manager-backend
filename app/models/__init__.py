from app.models.area import Area
from app.models.permission import Permission
from app.models.profile import Profile
from app.models.audit import AuditLog
from app.models.employee import Employee
from app.models.employee_extended import (  # noqa: F401 — registra modelos referenciados por Employee
    EmployeeAbsenceRecord,
    EmployeeCompetencyEvaluation,
    EmployeeContractHistory,
    EmployeeDisciplinaryAction,
    EmployeeDrivingLicense,
    EmployeeLanguage,
    EmployeePerformanceReview,
    EmployeeRecognition,
    EmployeeSalaryHistory,
    EmployeeSoftwareSkill,
    EmployeeSstAccident,
    EmployeeSstIncapacity,
    EmployeeSstPeriodicExam,
    EmployeeSstPpe,
    EmployeeSstProfile,
    EmployeeWorkSstCert,
)
from app.models.employee_career import EmployeeEducation, EmployeePriorJob, EmployeeTraining
from app.models.employee_custom import (
    EmployeeCustomFieldDef,
    EmployeeCustomFieldValue,
    EmployeePayrollEntry,
)
from app.models.employee_document import EmployeeDocument
from app.models.employee_profile import EmployeeDependent, EmployeeLabor, EmployeePersonal
from app.models.org_chart_layout import OrgChartLayoutEdge, OrgChartLayoutNode
from app.models.incapacity import IncapacityComment, IncapacityExtension, IncapacityNote, IncapacityNoteHistory
from app.models.incapacity_catalog import Diagnosis, EpsArlEntity, TemporalCategory
from app.models.absenteeism import AbsenteeismRecord
from app.models.overtime import OvertimeRequest, OvertimeRequestHistory
from app.models.shift import ShiftSchedule
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.app_notification import AppNotification

__all__ = [
    "AppNotification",
    "Area",
    "Permission",
    "Profile",
    "AuditLog",
    "Employee",
    "EmployeeEducation",
    "EmployeeDocument",
    "EmployeePriorJob",
    "EmployeeTraining",
    "EmployeeCustomFieldDef",
    "EmployeeCustomFieldValue",
    "EmployeePayrollEntry",
    "EmployeeDependent",
    "EmployeeLabor",
    "EmployeePersonal",
    "OrgChartLayoutEdge",
    "OrgChartLayoutNode",
    "Diagnosis",
    "EpsArlEntity",
    "IncapacityComment",
    "IncapacityExtension",
    "IncapacityNote",
    "IncapacityNoteHistory",
    "TemporalCategory",
    "AbsenteeismRecord",
    "OvertimeRequest",
    "OvertimeRequestHistory",
    "ShiftSchedule",
    "RefreshToken",
    "User",
]
