import pytest

from shared.base_exception import UnauthorizedError
from shared.security import create_access_token, decode_token, hash_password, verify_password


def test_hash_and_verify_correct_password():
    hashed = hash_password("SecurePass1")
    assert verify_password("SecurePass1", hashed) is True


def test_verify_wrong_password_returns_false():
    hashed = hash_password("SecurePass1")
    assert verify_password("WrongPass99", hashed) is False


def test_create_and_decode_access_token():
    token = create_access_token("user-uuid-123", "researcher")
    payload = decode_token(token)
    assert payload["sub"] == "user-uuid-123"
    assert payload["role"] == "researcher"


def test_decode_invalid_token_raises_unauthorized():
    with pytest.raises(UnauthorizedError):
        decode_token("not.a.valid.token")


def test_decode_tampered_token_raises_unauthorized():
    token = create_access_token("user-uuid-123", "researcher")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(UnauthorizedError):
        decode_token(tampered)
