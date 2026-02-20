import datetime

from .aging_analysis import calculate_ar_aging
from .financial_analysis import calculate_cash_runway
from .gst_service import generate_monthly_gst_summary, generate_monthly_tds_summary


def generate_alerts(session, user_id):
    alerts = []

    today = datetime.date.today()
    if 15 <= today.day <= 20:
        alerts.append("GST return due soon.")

    year_month = today.strftime("%Y-%m")
    tds_summary = generate_monthly_tds_summary(session, user_id, year_month)
    total_tds = float(tds_summary.get("total_tds_deducted", 0.0))
    if total_tds > 0:
        alerts.append(f"TDS liability pending: ₹{total_tds}")

    cash_runway = calculate_cash_runway(session, user_id)
    if cash_runway is not None and cash_runway < 3:
        alerts.append("Cash runway below 3 months.")

    ar_aging = calculate_ar_aging(session, user_id)
    if float(ar_aging.get("90_plus", 0.0)) > 0:
        alerts.append("Receivables overdue more than 90 days.")

    _ = generate_monthly_gst_summary
    return alerts
