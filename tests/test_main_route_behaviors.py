from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.auth import create_access_token
from app.database import Base


def build_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def build_client(monkeypatch):
    SessionLocal = build_session_factory()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main_module.Base.metadata, "create_all", lambda *args, **kwargs: None)
    main_module.app.dependency_overrides[main_module.get_db] = override_get_db

    client = TestClient(main_module.app)
    return client


def test_root_and_health_routes(monkeypatch):
    client = build_client(monkeypatch)
    try:
        root = client.get("/")
        health = client.get("/health")

        assert root.status_code == 200
        assert health.status_code == 200
        assert root.json()["message"]
        assert health.json() == {"status": "ok"}
    finally:
        main_module.app.dependency_overrides.clear()
        client.close()


def test_register_duplicate_email_returns_400(monkeypatch):
    client = build_client(monkeypatch)
    try:
        payload = {"email": "dup@example.com", "password": "Pass#123", "role": "business"}
        first = client.post("/register", json=payload)
        duplicate = client.post("/register", json=payload)

        assert first.status_code == 200
        assert duplicate.status_code == 400
        assert duplicate.json()["detail"] == "Email already registered"
    finally:
        main_module.app.dependency_overrides.clear()
        client.close()


def test_login_invalid_credentials_returns_401(monkeypatch):
    client = build_client(monkeypatch)
    try:
        client.post(
            "/register",
            json={"email": "login_invalid@example.com", "password": "Pass#123", "role": "business"},
        )

        wrong_password = client.post(
            "/login",
            json={"email": "login_invalid@example.com", "password": "WrongPass#321"},
        )
        unknown_user = client.post(
            "/login",
            json={"email": "missing@example.com", "password": "Pass#123"},
        )

        assert wrong_password.status_code == 401
        assert unknown_user.status_code == 401
    finally:
        main_module.app.dependency_overrides.clear()
        client.close()


def test_refresh_without_cookie_returns_401(monkeypatch):
    client = build_client(monkeypatch)
    try:
        response = client.post("/refresh")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing refresh token cookie"
    finally:
        main_module.app.dependency_overrides.clear()
        client.close()


def test_logout_without_cookie_still_returns_200(monkeypatch):
    client = build_client(monkeypatch)
    try:
        response = client.post("/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"
    finally:
        main_module.app.dependency_overrides.clear()
        client.close()


def test_admin_middleware_requires_bearer_for_admin_prefix(monkeypatch):
    client = build_client(monkeypatch)
    try:
        response = client.get("/admin/gst-rates")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing bearer token"
    finally:
        main_module.app.dependency_overrides.clear()
        client.close()


def test_admin_middleware_allows_admin_token_to_reach_route(monkeypatch):
    client = build_client(monkeypatch)
    try:
        admin_token = create_access_token({"sub": "1", "role": "admin"})
        response = client.get(
            "/admin/gst-rates",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404
    finally:
        main_module.app.dependency_overrides.clear()
        client.close()
