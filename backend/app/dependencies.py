from typing import Callable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.postgres import get_db_session
from modules.auth.exceptions import AccountInactiveError
from modules.users.models import User
from modules.users.repository import UserRepository
from shared.base_exception import ForbiddenError, UnauthorizedError
from shared.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if token is None:
        raise UnauthorizedError("Missing bearer token")
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")
    user = await UserRepository.find_by_id(session, user_id)
    if not user:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise AccountInactiveError()
    return user


def require_role(*roles: str) -> Callable:
    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        role_val = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
        if role_val not in roles:
            raise ForbiddenError("Insufficient permissions")
        return current_user
    return _dependency


require_admin = require_role("admin")
require_researcher_or_above = require_role("admin", "researcher")
