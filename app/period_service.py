from datetime import datetime

from .accounting_engine import generate_profit_and_loss
from .audit_service import log_action
from .gst_service import generate_monthly_gst_summary, generate_monthly_tds_summary
from .models import AccountingPeriod


def close_period(session, user_id, year_month):
    existing_period = (
        session.query(AccountingPeriod)
        .filter(
            AccountingPeriod.user_id == user_id,
            AccountingPeriod.year_month == year_month,
            AccountingPeriod.is_closed.is_(True),
        )
        .first()
    )
    if existing_period is not None:
        return {"message": "Period already closed."}

    generate_monthly_gst_summary(session, user_id, year_month)
    generate_monthly_tds_summary(session, user_id, year_month)
    generate_profit_and_loss(session, user_id)

    accounting_period = AccountingPeriod(
        user_id=user_id,
        year_month=year_month,
        is_closed=True,
        closed_at=datetime.utcnow(),
    )
    session.add(accounting_period)
    session.commit()
    session.refresh(accounting_period)
    log_action(
        session=session,
        user_id=user_id,
        action="CLOSE",
        entity_type="Period",
        entity_id=accounting_period.id,
        metadata={"year_month": year_month},
    )

    return {"message": "Period closed successfully."}
