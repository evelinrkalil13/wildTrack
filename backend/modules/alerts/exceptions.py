from shared.base_exception import NotFoundError


class AlertNotFoundError(NotFoundError):
    code = "ALERT_NOT_FOUND"
    message = "Alert not found"
