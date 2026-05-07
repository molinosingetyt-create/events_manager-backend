import enum


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    LEADER = "LEADER"
    HR = "HR"
    MANAGEMENT = "MANAGEMENT"


class EntityStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class IncapacityType(str, enum.Enum):
    GENERAL_ILLNESS = "general_illness"
    WORK_ACCIDENT = "work_accident"


class LongAbsenceDocumentKind(str, enum.Enum):
    """Documentación exigida cuando la incapacidad es de 3 o más días (inclusive)."""

    HISTORIA_CLINICA = "historia_clinica"
    INCAPACIDAD_EPS = "incapacidad_eps"


class OvertimeHistoryAction(str, enum.Enum):
    CREATED = "created"
    APPROVED = "approved"
    REJECTED = "rejected"
    UPDATED = "updated"


class IncapacityHistoryAction(str, enum.Enum):
    CREATED = "created"
    APPROVED = "approved"
    REJECTED = "rejected"
    UPDATED = "updated"
    EXTENSION_ADDED = "extension_added"


class EpsArlKind(str, enum.Enum):
    """Tipo de entidad de salud / riesgos laborales."""

    EPS = "eps"
    ARL = "arl"


class AppNotificationKind(str, enum.Enum):
    """Tipos de notificación in-app."""

    OVERTIME_PENDING = "overtime_pending"
    OVERTIME_DECIDED = "overtime_decided"
