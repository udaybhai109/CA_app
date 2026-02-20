import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
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


def get_route(path: str):
    for route in main_module.app.routes:
        if getattr(route, "path", None) == path:
            return route
    raise AssertionError(f"Route not found: {path}")


def test_close_period_rbac():
    session = build_session()
    close_period_route = get_route("/close-period/{user_id}/{year_month}")

    business_user = User(email="business_user@example.com", role="business")
    ca_user = User(email="ca_user@example.com", role="ca")
    session.add_all([business_user, ca_user])
    session.commit()
    session.refresh(business_user)
    session.refresh(ca_user)

    with pytest.raises(Exception, match="Unauthorized action"):
        close_period_route.endpoint(user_id=business_user.id, year_month="2025-06", db=session)

    result = close_period_route.endpoint(user_id=ca_user.id, year_month="2025-06", db=session)
    assert result["message"] == "Period closed successfully."
