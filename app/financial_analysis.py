from sqlalchemy.orm import Session

from .accounting_engine import generate_balance_sheet, generate_profit_and_loss


def calculate_current_ratio(session: Session, user_id: int):
    balance_sheet = generate_balance_sheet(session, user_id)
    current_assets = float(sum(balance_sheet.get("assets", {}).values()))
    current_liabilities = float(sum(balance_sheet.get("liabilities", {}).values()))

    if current_liabilities == 0:
        return None

    return float(current_assets / current_liabilities)


def calculate_net_profit_margin(session: Session, user_id: int):
    pnl = generate_profit_and_loss(session, user_id)
    total_revenue = float(pnl.get("total_revenue", 0.0))
    net_profit = float(pnl.get("net_profit", 0.0))

    if total_revenue == 0:
        return None

    return float(net_profit / total_revenue)


def calculate_cash_runway(session: Session, user_id: int):
    balance_sheet = generate_balance_sheet(session, user_id)
    pnl = generate_profit_and_loss(session, user_id)

    cash_balance = float(balance_sheet.get("assets", {}).get("Cash", 0.0))
    monthly_expense = float(pnl.get("total_expenses", 0.0))

    if monthly_expense == 0:
        return None

    return float(cash_balance / monthly_expense)
