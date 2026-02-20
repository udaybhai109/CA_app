import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.advisory_agent as advisory_agent_module
from app.accounting_engine import create_transaction
from app.database import Base
from app.models import AccountType, LedgerAccount, User


class DummyToolFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class DummyToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.type = "function"
        self.function = DummyToolFunction(name, arguments)


class DummyMessage:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class DummyChoice:
    def __init__(self, message):
        self.message = message


class DummyResponse:
    def __init__(self, message):
        self.choices = [DummyChoice(message)]


class FakeCompletions:
    def __init__(self):
        self.call_count = 0

    def create(self, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            return DummyResponse(
                DummyMessage(tool_calls=[DummyToolCall("tool_call_1", "pnl", "{}")])
            )

        tool_messages = [m for m in kwargs["messages"] if m.get("role") == "tool"]
        assert tool_messages
        tool_payload = json.loads(tool_messages[-1]["content"])
        assert tool_payload["net_profit"] == 30000.0

        return DummyResponse(DummyMessage(content="Your net profit is 30000.0."))


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeOpenAI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.chat = FakeChat()


def build_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def seed_user_data(session):
    user = User(email="advisory_tool_user@example.com")
    session.add(user)
    session.flush()

    cash_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    sales_revenue_account = LedgerAccount(
        name="Sales Revenue", account_type=AccountType.REVENUE, user_id=user.id
    )
    office_expense_account = LedgerAccount(
        name="Office Expense", account_type=AccountType.EXPENSE, user_id=user.id
    )
    owner_capital_account = LedgerAccount(
        name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id
    )
    session.add_all([cash_account, sales_revenue_account, office_expense_account, owner_capital_account])
    session.commit()
    session.refresh(user)
    session.refresh(cash_account)
    session.refresh(sales_revenue_account)
    session.refresh(office_expense_account)
    session.refresh(owner_capital_account)

    create_transaction(
        session=session,
        user_id=user.id,
        description="Owner invests into business",
        debit_account_id=cash_account.id,
        credit_account_id=owner_capital_account.id,
        amount=100000.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Business earns revenue",
        debit_account_id=cash_account.id,
        credit_account_id=sales_revenue_account.id,
        amount=50000.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Business pays office expense",
        debit_account_id=office_expense_account.id,
        credit_account_id=cash_account.id,
        amount=20000.0,
    )

    return user


def test_advisory_agent_tool_calling_net_profit(monkeypatch):
    session = build_session()
    user = seed_user_data(session)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(advisory_agent_module, "OpenAI", FakeOpenAI)

    response = advisory_agent_module.generate_advice(
        session=session,
        user_id=user.id,
        question="What is my net profit?",
    )

    assert "30000" in response
