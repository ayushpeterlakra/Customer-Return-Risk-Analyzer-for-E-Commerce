import enum


class OrderStatus(str, enum.Enum):
    PLACED = "PLACED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class ReturnStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REFUNDED = "REFUNDED"


class ReasonCode(str, enum.Enum):
    DEFECTIVE = "DEFECTIVE"
    NOT_WORKING = "NOT_WORKING"
    WRONG_ITEM = "WRONG_ITEM"
    DAMAGED_IN_TRANSIT = "DAMAGED_IN_TRANSIT"
    SIZE_FIT = "SIZE_FIT"
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"
    CHANGED_MIND = "CHANGED_MIND"
    OTHER = "OTHER"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ScoringMethod(str, enum.Enum):
    RULE_BASED = "RULE_BASED"
    ML = "ML"


class ReviewStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"
    REVIEWED = "REVIEWED"
    ESCALATED = "ESCALATED"
