from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.postgres import get_db_session
from modules.auth.exceptions import AccountInactiveError
from modules.users.models import User
from modules.users.repository import UserRepository
from shared.base_exception import UnauthorizedError
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
