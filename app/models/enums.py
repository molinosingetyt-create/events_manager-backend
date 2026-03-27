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
    INCAPACITY = "incapacity"
    NOTE = "note"


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


class AppNotificationKind(str, enum.Enum):
    """Tipos de notificación in-app."""

    OVERTIME_PENDING = "overtime_pending"
    OVERTIME_DECIDED = "overtime_decided"
