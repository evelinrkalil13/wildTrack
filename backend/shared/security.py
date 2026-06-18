import base64
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from shared.base_exception import UnauthorizedError
from shared.config import get_settings

_BCRYPT_ROUNDS = 12


def _prepare(plaintext: str) -> bytes:
    # SHA-256 → base64 keeps input at 44 bytes, within bcrypt's 72-byte limit.
    return base64.b64encode(hashlib.sha256(plaintext.encode()).digest())


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(_prepare(plaintext), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(plaintext: str, hashed: str) -> bool:
    return bcrypt.checkpw(_prepare(plaintext), hashed.encode())


def create_access_token(user_id: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=settings.jwt_expiry_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
