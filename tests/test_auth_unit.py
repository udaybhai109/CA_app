from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_token,
)


def test_password_hash_and_verify_roundtrip():
    raw_password = "SecurePassword#42"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed)


def test_verify_password_handles_missing_hash():
    assert verify_password("abc123", None) is False


def test_create_access_token_and_verify_token_payload():
    token = create_access_token({"sub": "101", "role": "business"})
    payload = verify_token(token)

    assert payload["sub"] == "101"
    assert payload["role"] == "business"
    assert payload["type"] == "access"


def test_verify_token_rejects_non_access_token_type():
    refresh_style_token = jwt.encode(
        {
            "sub": "111",
            "role": "business",
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(minutes=5),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(HTTPException, match="Could not validate credentials"):
        verify_token(refresh_style_token)


def test_verify_token_rejects_invalid_signature():
    valid = create_access_token({"sub": "222", "role": "admin"})
    tampered = valid[:-1] + ("a" if valid[-1] != "a" else "b")

    with pytest.raises(HTTPException, match="Could not validate credentials"):
        verify_token(tampered)


def test_hash_refresh_token_deterministic_and_unique():
    token_a = "refresh-token-a"
    token_b = "refresh-token-b"

    assert hash_refresh_token(token_a) == hash_refresh_token(token_a)
    assert hash_refresh_token(token_a) != hash_refresh_token(token_b)


def test_create_refresh_token_returns_future_expiry():
    refresh_token, expires_at = create_refresh_token()

    assert isinstance(refresh_token, str)
    assert refresh_token
    assert expires_at > datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS - 1)


def test_access_token_expiry_claim_is_present_and_future():
    token = create_access_token({"sub": "333", "role": "ca"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["type"] == "access"
    assert payload["exp"] > (datetime.utcnow() + timedelta(minutes=10)).timestamp()
    assert payload["exp"] < (datetime.utcnow() + timedelta(hours=12)).timestamp()
