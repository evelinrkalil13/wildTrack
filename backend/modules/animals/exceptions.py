from shared.base_exception import ConflictError, NotFoundError


class AnimalNotFoundError(NotFoundError):
    message = "Animal not found"
    code = "NOT_FOUND"


class RfidTagConflictError(ConflictError):
    message = "An animal with this RFID tag already exists"
    code = "RFID_TAG_EXISTS"
