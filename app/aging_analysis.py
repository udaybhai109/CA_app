import datetime

from sqlalchemy.orm import Session

from .models import Invoice


def calculate_ar_aging(session: Session, user_id: int) -> dict:
    today = datetime.date.today()
    buckets = {"0_30": 0.0, "31_60": 0.0, "61_90": 0.0, "90_plus": 0.0}

    invoices = (
        session.query(Invoice)
        .filter(Invoice.user_id == user_id, Invoice.transaction_type == "sale")
        .all()
    )

    for invoice in invoices:
        days_outstanding = (today - invoice.invoice_date).days
        amount = float(invoice.total_amount)

        if days_outstanding <= 30:
            buckets["0_30"] += amount
        elif days_outstanding <= 60:
            buckets["31_60"] += amount
        elif days_outstanding <= 90:
            buckets["61_90"] += amount
        else:
            buckets["90_plus"] += amount

    return {key: float(value) for key, value in buckets.items()}


def calculate_ap_aging(session: Session, user_id: int) -> dict:
    today = datetime.date.today()
    buckets = {"0_30": 0.0, "31_60": 0.0, "61_90": 0.0, "90_plus": 0.0}

    invoices = (
        session.query(Invoice)
        .filter(Invoice.user_id == user_id, Invoice.transaction_type == "purchase")
        .all()
    )

    for invoice in invoices:
        days_outstanding = (today - invoice.invoice_date).days
        amount = float(invoice.total_amount)

        if days_outstanding <= 30:
            buckets["0_30"] += amount
        elif days_outstanding <= 60:
            buckets["31_60"] += amount
        elif days_outstanding <= 90:
            buckets["61_90"] += amount
        else:
            buckets["90_plus"] += amount

    return {key: float(value) for key, value in buckets.items()}
