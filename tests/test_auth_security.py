from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.auth import ALGORITHM, SECRET_KEY, hash_refresh_token, verify_password
from app.database import Base
from app.models import RefreshToken, User


@pytest.fixture()
def client_and_db(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main_module.Base.metadata, "create_all", lambda *args, **kwargs: None)
    main_module.app.dependency_overrides[main_module.get_db] = override_get_db

    with TestClient(main_module.app) as client:
        yield client, SessionLocal

    main_module.app.dependency_overrides.clear()


def register_user(client: TestClient, email: str, password: str, role: str = "business") -> int:
    response = client.post(
        "/register",
        json={"email": email, "password": password, "role": role},
    )
    assert response.status_code == 200
    return int(response.json()["id"])


def login_user(client: TestClient, email: str, password: str) -> str:
    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200
    token = response.json().get("access_token")
    assert isinstance(token, str) and token
    return token


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_new_user_and_password_is_hashed(client_and_db):
    client, SessionLocal = client_and_db

    email = "secure_register@example.com"
    raw_password = "StrongPass#123"
    user_id = register_user(client, email, raw_password)

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.email == email
        assert user.password_hash is not None
        assert user.password_hash != raw_password
        assert verify_password(raw_password, user.password_hash)


def test_login_returns_access_token_and_refresh_token_is_hashed(client_and_db):
    client, SessionLocal = client_and_db

    email = "secure_login@example.com"
    password = "StrongPass#123"
    user_id = register_user(client, email, password)
    access_token = login_user(client, email, password)
    assert access_token

    refresh_cookie = client.cookies.get(main_module.REFRESH_COOKIE_NAME)
    assert refresh_cookie

    with SessionLocal() as db:
        tokens = db.query(RefreshToken).filter(RefreshToken.user_id == user_id).all()
        assert len(tokens) == 1
        assert tokens[0].token == hash_refresh_token(refresh_cookie)
        assert tokens[0].token != refresh_cookie


def test_refresh_token_rotates_correctly(client_and_db):
    client, SessionLocal = client_and_db

    email = "rotate_refresh@example.com"
    password = "StrongPass#123"
    user_id = register_user(client, email, password)
    _ = login_user(client, email, password)

    old_refresh = client.cookies.get(main_module.REFRESH_COOKIE_NAME)
    assert old_refresh
    old_hashed = hash_refresh_token(old_refresh)

    refresh_response = client.post("/refresh")
    assert refresh_response.status_code == 200
    assert refresh_response.json().get("access_token")

    new_refresh = client.cookies.get(main_module.REFRESH_COOKIE_NAME)
    assert new_refresh
    assert new_refresh != old_refresh
    new_hashed = hash_refresh_token(new_refresh)

    with SessionLocal() as db:
        tokens = db.query(RefreshToken).filter(RefreshToken.user_id == user_id).all()
        assert len(tokens) == 1
        assert tokens[0].token == new_hashed
        assert tokens[0].token != old_hashed


def test_expired_access_token_triggers_refresh_flow(client_and_db):
    client, _ = client_and_db

    email = "expired_flow@example.com"
    password = "StrongPass#123"
    user_id = register_user(client, email, password)
    _ = login_user(client, email, password)

    expired_token = jwt.encode(
        {
            "sub": str(user_id),
            "role": "business",
            "type": "access",
            "exp": datetime.utcnow() - timedelta(minutes=1),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    expired_response = client.get(f"/forecast/{user_id}", headers=auth_header(expired_token))
    assert expired_response.status_code == 401

    refresh_response = client.post("/refresh")
    assert refresh_response.status_code == 200
    new_access = refresh_response.json().get("access_token")
    assert isinstance(new_access, str) and new_access

    retry_response = client.get(f"/forecast/{user_id}", headers=auth_header(new_access))
    assert retry_response.status_code == 200


def test_logout_invalidates_refresh_token(client_and_db):
    client, SessionLocal = client_and_db

    email = "logout_flow@example.com"
    password = "StrongPass#123"
    user_id = register_user(client, email, password)
    _ = login_user(client, email, password)

    logout_response = client.post("/logout")
    assert logout_response.status_code == 200

    refresh_response = client.post("/refresh")
    assert refresh_response.status_code == 401

    with SessionLocal() as db:
        tokens = db.query(RefreshToken).filter(RefreshToken.user_id == user_id).all()
        assert len(tokens) == 0


def test_cannot_access_protected_route_without_token(client_and_db):
    client, _ = client_and_db
    response = client.get("/forecast/1")
    assert response.status_code in (401, 403)


def test_business_user_cannot_access_admin_routes(client_and_db):
    client, _ = client_and_db

    email = "business_admin_block@example.com"
    password = "StrongPass#123"
    register_user(client, email, password, role="business")
    business_token = login_user(client, email, password)

    response = client.get("/admin/gst-rates", headers=auth_header(business_token))
    assert response.status_code == 403


def test_ca_can_close_period_and_business_cannot(client_and_db):
    client, _ = client_and_db

    business_email = "business_close_block@example.com"
    ca_email = "ca_close_allow@example.com"
    password = "StrongPass#123"

    business_user_id = register_user(client, business_email, password, role="business")
    business_token = login_user(client, business_email, password)

    blocked_response = client.post(
        f"/close-period/{business_user_id}/2025-06",
        headers=auth_header(business_token),
    )
    assert blocked_response.status_code == 403

    ca_user_id = register_user(client, ca_email, password, role="ca")
    ca_token = login_user(client, ca_email, password)

    allowed_response = client.post(
        f"/close-period/{ca_user_id}/2025-06",
        headers=auth_header(ca_token),
    )
    assert allowed_response.status_code == 200
    assert allowed_response.json().get("message") in {
        "Period closed successfully.",
        "Period already closed.",
    }


def test_jwt_tampering_fails(client_and_db):
    client, _ = client_and_db

    email = "tamper_case@example.com"
    password = "StrongPass#123"
    user_id = register_user(client, email, password)
    valid_token = login_user(client, email, password)

    tampered_token = valid_token[:-1] + ("a" if valid_token[-1] != "a" else "b")
    response = client.get(f"/forecast/{user_id}", headers=auth_header(tampered_token))
    assert response.status_code == 401
