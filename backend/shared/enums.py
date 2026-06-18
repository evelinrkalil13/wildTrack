import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    researcher = "researcher"
    field_operator = "field_operator"
