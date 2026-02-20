import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import create_access_token, get_current_user, require_privileged_user
from app.database import Base
from app.models import User


def build_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def test_get_current_user_returns_matching_user():
    session = build_session()
    user = User(email="dep_user@example.com", role="business")
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    current_user = get_current_user(credentials=credentials, db=session)

    assert current_user.id == user.id
    assert current_user.email == "dep_user@example.com"


def test_get_current_user_raises_if_user_not_found():
    session = build_session()
    token = create_access_token({"sub": "99999", "role": "business"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException, match="User not found for token"):
        get_current_user(credentials=credentials, db=session)


def test_require_privileged_user_allows_ca_and_admin():
    ca_user = User(email="ca_dep@example.com", role="ca")
    admin_user = User(email="admin_dep@example.com", role="admin")

    assert require_privileged_user(ca_user).role == "ca"
    assert require_privileged_user(admin_user).role == "admin"


def test_require_privileged_user_rejects_business():
    business_user = User(email="biz_dep@example.com", role="business")
    with pytest.raises(HTTPException, match="Forbidden: admin or CA role required"):
        require_privileged_user(business_user)
