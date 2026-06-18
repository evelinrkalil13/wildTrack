import re

from pydantic import BaseModel, EmailStr, field_validator

from modules.users.schemas import UserRead, UserSummary


class RegisterRequest(BaseModel):
    name: str
    document: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 255:
            raise ValueError("Name must be between 2 and 255 characters")
        return v

    @field_validator("document")
    @classmethod
    def validate_document(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5 or len(v) > 50:
            raise ValueError("Document must be between 5 and 50 characters")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8 or len(v) > 128:
            raise ValueError("Password must be between 8 and 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_login_password(cls, v: str) -> str:
        if not v:
            raise ValueError("Password must not be empty")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary


class MeResponse(UserRead):
    pass
