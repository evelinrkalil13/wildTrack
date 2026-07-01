import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    researcher = "researcher"
    field_operator = "field_operator"


class StationStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"
    offline = "offline"


class StationUserRole(str, enum.Enum):
    owner = "owner"
    researcher = "researcher"
    field_operator = "field_operator"


class DeviceStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    unassigned = "unassigned"


class AnimalSex(str, enum.Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class AlertType(str, enum.Enum):
    rfid_read_failure = "rfid_read_failure"
    connectivity_lost = "connectivity_lost"
    sensor_failure = "sensor_failure"
    inactive_station = "inactive_station"
    empty_tank = "empty_tank"
    camera_failure = "camera_failure"
