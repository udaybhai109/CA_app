import importlib
import inspect

import app.database as database_module
import app.main as main_module


def get_route(path: str):
    for route in main_module.app.routes:
        if getattr(route, "path", None) == path:
            return route
    raise AssertionError(f"Route not found: {path}")


def test_no_circular_imports():
    importlib.reload(importlib.import_module("app.database"))
    importlib.reload(importlib.import_module("app.accounting_engine"))
    importlib.reload(importlib.import_module("app.advisory_agent"))
    module = importlib.reload(importlib.import_module("app.main"))
    assert hasattr(module, "app")


def test_main_imports_get_db_from_database():
    assert main_module.get_db is database_module.get_db


def test_correct_function_names_available():
    assert callable(main_module.generate_profit_and_loss)
    assert callable(main_module.generate_balance_sheet)
    assert callable(main_module.generate_advice)


def test_pnl_endpoint_uses_generate_profit_and_loss(monkeypatch):
    route = get_route("/pnl/{user_id}")
    called = {}
    expected = {
        "revenues": {"Service Revenue": 100.0},
        "expenses": {"Rent Expense": 40.0},
        "total_revenue": 100.0,
        "total_expenses": 40.0,
        "net_profit": 60.0,
    }
    dummy_session = object()

    def fake_generate_profit_and_loss(session, user_id):
        called["session"] = session
        called["user_id"] = user_id
        return expected

    monkeypatch.setattr(main_module, "generate_profit_and_loss", fake_generate_profit_and_loss)

    result = route.endpoint(user_id=7, db=dummy_session)

    assert result == expected
    assert called["session"] is dummy_session
    assert called["user_id"] == 7


def test_balance_sheet_endpoint_uses_generate_balance_sheet(monkeypatch):
    route = get_route("/balance-sheet/{user_id}")
    called = {}
    expected = {
        "assets": {"Cash": 300.0},
        "liabilities": {"Loan Payable": 100.0},
        "equity": {"Owner Capital": 200.0},
        "total_assets": 300.0,
        "total_liabilities": 100.0,
        "total_equity": 200.0,
    }
    dummy_session = object()

    def fake_generate_balance_sheet(session, user_id):
        called["session"] = session
        called["user_id"] = user_id
        return expected

    monkeypatch.setattr(main_module, "generate_balance_sheet", fake_generate_balance_sheet)

    result = route.endpoint(user_id=9, db=dummy_session)

    assert result == expected
    assert called["session"] is dummy_session
    assert called["user_id"] == 9


def test_advice_endpoint_uses_generate_advice_with_question(monkeypatch):
    route = get_route("/advice/{user_id}")
    called = {}
    dummy_session = object()

    def fake_generate_advice(session, user_id, question):
        called["session"] = session
        called["user_id"] = user_id
        called["question"] = question
        assert session is dummy_session
        assert user_id == 11
        return "Net profit is healthy."

    monkeypatch.setattr(main_module, "generate_advice", fake_generate_advice)

    result = route.endpoint(user_id=11, question="What is my net profit?", db=dummy_session)

    assert result == "Net profit is healthy."
    assert called["session"] is dummy_session
    assert called["user_id"] == 11
    assert called["question"] == "What is my net profit?"


def test_db_session_properly_closed():
    closed_state = {"closed": False}

    class DummySession:
        def close(self):
            closed_state["closed"] = True

    dummy_session = DummySession()
    original_session_local = database_module.SessionLocal
    database_module.SessionLocal = lambda: dummy_session
    try:
        db_gen = database_module.get_db()
        yielded = next(db_gen)
        assert yielded is dummy_session
        assert closed_state["closed"] is False
        db_gen.close()
        assert closed_state["closed"] is True
    finally:
        database_module.SessionLocal = original_session_local


def test_endpoint_dependencies_use_get_db():
    pnl_dep = inspect.signature(main_module.get_profit_and_loss).parameters["db"].default
    bs_dep = inspect.signature(main_module.get_balance_sheet).parameters["db"].default
    advice_dep = inspect.signature(main_module.get_advice).parameters["db"].default

    assert pnl_dep.dependency is main_module.get_db
    assert bs_dep.dependency is main_module.get_db
    assert advice_dep.dependency is main_module.get_db


def test_no_async_sync_mismatch_for_sqlalchemy_routes():
    assert not inspect.iscoroutinefunction(get_route("/pnl/{user_id}").endpoint)
    assert not inspect.iscoroutinefunction(get_route("/balance-sheet/{user_id}").endpoint)
    assert not inspect.iscoroutinefunction(get_route("/advice/{user_id}").endpoint)
