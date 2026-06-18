from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.exceptions import AccountInactiveError, EmailAlreadyExistsError, InvalidCredentialsError
from modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from modules.users.models import User
from modules.users.repository import UserRepository
from modules.users.schemas import UserSummary
from shared.config import get_settings
from shared.enums import UserRole
from shared.security import create_access_token, hash_password, verify_password
from shared.uuid7 import generate_uuid7


class AuthService:
    @staticmethod
    async def register(session: AsyncSession, data: RegisterRequest) -> User:
        existing = await UserRepository.find_by_email(session, data.email)
        if existing:
            raise EmailAlreadyExistsError()
        return await UserRepository.create(
            session,
            {
                "id": generate_uuid7(),
                "name": data.name,
                "document": data.document,
                "email": data.email,
                "password_hash": hash_password(data.password),
                "role": UserRole.researcher,
            },
        )

    @staticmethod
    async def login(session: AsyncSession, data: LoginRequest) -> TokenResponse:
        user = await UserRepository.find_by_email(session, data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise AccountInactiveError()
        settings = get_settings()
        role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        token = create_access_token(str(user.id), role_str)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.jwt_expiry_seconds,
            user=UserSummary.model_validate(user),
        )
