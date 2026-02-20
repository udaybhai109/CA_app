from datetime import date

from .accounting_engine import generate_balance_sheet, generate_profit_and_loss
from .aging_analysis import calculate_ap_aging, calculate_ar_aging
from .financial_analysis import calculate_cash_runway, calculate_current_ratio, calculate_net_profit_margin
from .gst_service import generate_monthly_gst_summary, generate_monthly_tds_summary


def run_tool(session, user_id, tool_name, params=None):
    tool_params = params or {}

    if tool_name == "pnl":
        return generate_profit_and_loss(session, user_id)

    if tool_name == "balance_sheet":
        return generate_balance_sheet(session, user_id)

    if tool_name == "gst_summary":
        year_month = tool_params.get("year_month") or date.today().strftime("%Y-%m")
        return generate_monthly_gst_summary(session, user_id, year_month)

    if tool_name == "tds_summary":
        year_month = tool_params.get("year_month") or date.today().strftime("%Y-%m")
        return generate_monthly_tds_summary(session, user_id, year_month)

    if tool_name == "financial_health":
        return {
            "current_ratio": calculate_current_ratio(session, user_id),
            "net_profit_margin": calculate_net_profit_margin(session, user_id),
            "cash_runway": calculate_cash_runway(session, user_id),
        }

    if tool_name == "aging":
        return {
            "accounts_receivable": calculate_ar_aging(session, user_id),
            "accounts_payable": calculate_ap_aging(session, user_id),
        }

    raise ValueError(f"Unsupported tool: {tool_name}")
