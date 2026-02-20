from datetime import datetime

from sqlalchemy.orm import Session

from .accounting_engine import generate_balance_sheet, generate_profit_and_loss
from .models import Invoice, InvoiceTransactionType


def _month_key(value: datetime) -> str:
    return value.strftime("%Y-%m")


def _first_day_of_month(value: datetime) -> datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_month(value: datetime) -> datetime:
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1, day=1)
    return value.replace(month=value.month + 1, day=1)


def _future_month_keys(months: int) -> list[str]:
    keys: list[str] = []
    cursor = _add_month(_first_day_of_month(datetime.utcnow()))
    for _ in range(months):
        keys.append(_month_key(cursor))
        cursor = _add_month(cursor)
    return keys


def _historical_month_count(session: Session, user_id: int) -> int:
    invoices = session.query(Invoice).filter(Invoice.user_id == user_id).all()
    month_keys = {
        invoice.invoice_date.strftime("%Y-%m")
        for invoice in invoices
        if invoice.invoice_date is not None
    }
    return len(month_keys)


def forecast_revenue(session: Session, user_id: int, months: int = 3) -> list[dict]:
    invoices = (
        session.query(Invoice)
        .filter(
            Invoice.user_id == user_id,
            Invoice.transaction_type == InvoiceTransactionType.SALE,
        )
        .all()
    )

    monthly_revenue: dict[str, float] = {}
    for invoice in invoices:
        month = invoice.invoice_date.strftime("%Y-%m")
        monthly_revenue[month] = monthly_revenue.get(month, 0.0) + float(invoice.total_amount or 0.0)

    average_monthly_revenue = (
        float(sum(monthly_revenue.values()) / len(monthly_revenue)) if monthly_revenue else 0.0
    )

    return [
        {"month": month, "projected_revenue": float(average_monthly_revenue)}
        for month in _future_month_keys(months)
    ]


def forecast_expenses(session: Session, user_id: int, months: int = 3) -> list[dict]:
    pnl = generate_profit_and_loss(session, user_id)
    total_expenses = float(pnl.get("total_expenses", 0.0))
    month_count = _historical_month_count(session, user_id)

    average_monthly_expense = (
        float(total_expenses / month_count) if month_count > 0 else float(total_expenses)
    )

    return [
        {"month": month, "projected_expense": float(average_monthly_expense)}
        for month in _future_month_keys(months)
    ]


def forecast_cash_balance(session: Session, user_id: int, months: int = 3) -> list[dict]:
    balance_sheet = generate_balance_sheet(session, user_id)
    current_cash = float(balance_sheet.get("assets", {}).get("Cash", 0.0))

    revenue_projection = forecast_revenue(session, user_id, months)
    expense_projection = forecast_expenses(session, user_id, months)

    projected: list[dict] = []
    running_balance = current_cash

    for index in range(months):
        projected_revenue = float(revenue_projection[index]["projected_revenue"])
        projected_expense = float(expense_projection[index]["projected_expense"])
        running_balance = running_balance + projected_revenue - projected_expense
        projected.append(
            {
                "month": revenue_projection[index]["month"],
                "projected_cash_balance": float(running_balance),
            }
        )

    return projected


def forecast_gst_liability(session: Session, user_id: int, months: int = 3) -> list[dict]:
    invoices = session.query(Invoice).filter(Invoice.user_id == user_id).all()

    monthly_output_gst: dict[str, float] = {}
    monthly_input_gst: dict[str, float] = {}

    for invoice in invoices:
        month = invoice.invoice_date.strftime("%Y-%m")
        total_gst = float((invoice.cgst or 0.0) + (invoice.sgst or 0.0) + (invoice.igst or 0.0))

        if invoice.transaction_type == InvoiceTransactionType.SALE:
            monthly_output_gst[month] = monthly_output_gst.get(month, 0.0) + total_gst
        elif invoice.transaction_type == InvoiceTransactionType.PURCHASE:
            monthly_input_gst[month] = monthly_input_gst.get(month, 0.0) + total_gst

    all_months = sorted(set(monthly_output_gst.keys()).union(monthly_input_gst.keys()))
    monthly_net_gst = [
        float(monthly_output_gst.get(month, 0.0) - monthly_input_gst.get(month, 0.0))
        for month in all_months
    ]

    average_monthly_gst_liability = (
        float(sum(monthly_net_gst) / len(monthly_net_gst)) if monthly_net_gst else 0.0
    )

    return [
        {"month": month, "projected_gst_liability": float(average_monthly_gst_liability)}
        for month in _future_month_keys(months)
    ]
