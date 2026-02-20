import datetime

import pytest

import app.ai_router as ai_router_module
import app.auth_utils as auth_utils_module
import app.tool_registry as tool_registry_module


class DummyUser:
    def __init__(self, role: str):
        self.role = role


def test_ai_router_routes_expected_keywords():
    assert ai_router_module.route_user_query("Show GST filing view") == "COMPLIANCE"
    assert ai_router_module.route_user_query("Need TDS summary") == "COMPLIANCE"
    assert ai_router_module.route_user_query("What is my profit today?") == "ACCOUNTING"
    assert ai_router_module.route_user_query("Generate balance sheet") == "ACCOUNTING"
    assert ai_router_module.route_user_query("How can I improve cash flow?") == "ADVISORY"


def test_check_role_allows_expected_role():
    auth_utils_module.check_role(DummyUser(role="ca"), ["ca", "admin"])


def test_check_role_raises_for_disallowed_role():
    with pytest.raises(Exception, match="Unauthorized action"):
        auth_utils_module.check_role(DummyUser(role="business"), ["ca", "admin"])


def test_tool_registry_pnl_dispatch(monkeypatch):
    dummy_session = object()

    def fake_pnl(session, user_id):
        assert session is dummy_session
        assert user_id == 10
        return {"net_profit": 123.0}

    monkeypatch.setattr(tool_registry_module, "generate_profit_and_loss", fake_pnl)

    result = tool_registry_module.run_tool(dummy_session, 10, "pnl")
    assert result == {"net_profit": 123.0}


def test_tool_registry_balance_sheet_dispatch(monkeypatch):
    def fake_balance_sheet(session, user_id):
        assert user_id == 11
        return {"total_assets": 400.0}

    monkeypatch.setattr(tool_registry_module, "generate_balance_sheet", fake_balance_sheet)

    result = tool_registry_module.run_tool(object(), 11, "balance_sheet")
    assert result == {"total_assets": 400.0}


def test_tool_registry_gst_summary_uses_default_month(monkeypatch):
    class FixedDate(datetime.date):
        @classmethod
        def today(cls):
            return cls(2025, 6, 20)

    def fake_gst_summary(session, user_id, year_month):
        assert user_id == 12
        assert year_month == "2025-06"
        return {"net_payable": 9000.0}

    monkeypatch.setattr(tool_registry_module, "date", FixedDate)
    monkeypatch.setattr(tool_registry_module, "generate_monthly_gst_summary", fake_gst_summary)

    result = tool_registry_module.run_tool(object(), 12, "gst_summary")
    assert result == {"net_payable": 9000.0}


def test_tool_registry_tds_summary_with_param(monkeypatch):
    def fake_tds_summary(session, user_id, year_month):
        assert user_id == 13
        assert year_month == "2025-07"
        return {"total_tds_deducted": 7500.0}

    monkeypatch.setattr(tool_registry_module, "generate_monthly_tds_summary", fake_tds_summary)

    result = tool_registry_module.run_tool(
        object(),
        13,
        "tds_summary",
        {"year_month": "2025-07"},
    )
    assert result == {"total_tds_deducted": 7500.0}


def test_tool_registry_financial_health_aggregation(monkeypatch):
    monkeypatch.setattr(tool_registry_module, "calculate_current_ratio", lambda *_: 2.5)
    monkeypatch.setattr(tool_registry_module, "calculate_net_profit_margin", lambda *_: 0.6)
    monkeypatch.setattr(tool_registry_module, "calculate_cash_runway", lambda *_: 6.5)

    result = tool_registry_module.run_tool(object(), 14, "financial_health")
    assert result == {
        "current_ratio": 2.5,
        "net_profit_margin": 0.6,
        "cash_runway": 6.5,
    }


def test_tool_registry_aging_aggregation(monkeypatch):
    monkeypatch.setattr(tool_registry_module, "calculate_ar_aging", lambda *_: {"90_plus": 500.0})
    monkeypatch.setattr(tool_registry_module, "calculate_ap_aging", lambda *_: {"0_30": 200.0})

    result = tool_registry_module.run_tool(object(), 15, "aging")
    assert result == {
        "accounts_receivable": {"90_plus": 500.0},
        "accounts_payable": {"0_30": 200.0},
    }


def test_tool_registry_unsupported_tool_raises():
    with pytest.raises(ValueError, match="Unsupported tool"):
        tool_registry_module.run_tool(object(), 16, "unknown_tool")
