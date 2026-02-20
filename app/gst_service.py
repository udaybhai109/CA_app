from datetime import datetime

from sqlalchemy.orm import Session

from .audit_service import log_action
from .compliance_engine import calculate_net_gst_liability, calculate_output_gst, calculate_tds
from .models import AccountingPeriod, Invoice, InvoiceTransactionType, TDSLiability, TaxLiability


def create_invoice_with_gst(
    session: Session,
    user_id: int,
    invoice_number: str,
    invoice_date,
    amount: float,
    gst_rate: float,
    transaction_type: str,
    is_interstate: bool,
) -> Invoice:
    if isinstance(invoice_date, str):
        parsed_invoice_date = datetime.strptime(invoice_date, "%Y-%m-%d").date()
    else:
        parsed_invoice_date = invoice_date

    invoice_month = parsed_invoice_date.strftime("%Y-%m")
    closed_period = (
        session.query(AccountingPeriod)
        .filter(
            AccountingPeriod.user_id == user_id,
            AccountingPeriod.year_month == invoice_month,
            AccountingPeriod.is_closed.is_(True),
        )
        .first()
    )
    if closed_period is not None:
        raise Exception("Period is closed. Cannot modify.")

    gst_details = calculate_output_gst(
        amount=amount,
        gst_rate=gst_rate,
        transaction_type=transaction_type,
        is_interstate=is_interstate,
    )

    if transaction_type == "sale":
        invoice_transaction_type = InvoiceTransactionType.SALE
    elif transaction_type == "purchase":
        invoice_transaction_type = InvoiceTransactionType.PURCHASE
    else:
        raise ValueError("transaction_type must be 'sale' or 'purchase'")

    invoice = Invoice(
        user_id=user_id,
        invoice_number=invoice_number,
        invoice_date=parsed_invoice_date,
        total_amount=float(amount),
        gst_rate=float(gst_rate),
        is_interstate=bool(is_interstate),
        transaction_type=invoice_transaction_type,
        cgst=float(gst_details["cgst"]),
        sgst=float(gst_details["sgst"]),
        igst=float(gst_details["igst"]),
    )

    try:
        session.add(invoice)
        session.commit()
        session.refresh(invoice)
        log_action(
            session=session,
            user_id=user_id,
            action="CREATE",
            entity_type="Invoice",
            entity_id=invoice.id,
            metadata={
                "invoice_number": invoice.invoice_number,
                "transaction_type": invoice.transaction_type.value,
                "amount": invoice.total_amount,
            },
        )
        return invoice
    except Exception:
        session.rollback()
        raise


def create_invoice_with_tds(
    session: Session,
    user_id: int,
    invoice_number: str,
    invoice_date,
    amount: float,
    gst_rate: float,
    transaction_type: str,
    is_interstate: bool,
    vendor_type: str,
) -> Invoice:
    if isinstance(invoice_date, str):
        parsed_invoice_date = datetime.strptime(invoice_date, "%Y-%m-%d").date()
    else:
        parsed_invoice_date = invoice_date

    invoice_month = parsed_invoice_date.strftime("%Y-%m")
    closed_period = (
        session.query(AccountingPeriod)
        .filter(
            AccountingPeriod.user_id == user_id,
            AccountingPeriod.year_month == invoice_month,
            AccountingPeriod.is_closed.is_(True),
        )
        .first()
    )
    if closed_period is not None:
        raise Exception("Period is closed. Cannot modify.")

    gst_details = calculate_output_gst(
        amount=amount,
        gst_rate=gst_rate,
        transaction_type=transaction_type,
        is_interstate=is_interstate,
    )
    tds_details = calculate_tds(amount=amount, vendor_type=vendor_type)

    if transaction_type == "sale":
        invoice_transaction_type = InvoiceTransactionType.SALE
    elif transaction_type == "purchase":
        invoice_transaction_type = InvoiceTransactionType.PURCHASE
    else:
        raise ValueError("transaction_type must be 'sale' or 'purchase'")

    invoice = Invoice(
        user_id=user_id,
        invoice_number=invoice_number,
        invoice_date=parsed_invoice_date,
        total_amount=float(amount),
        gst_rate=float(gst_rate),
        is_interstate=bool(is_interstate),
        transaction_type=invoice_transaction_type,
        cgst=float(gst_details["cgst"]),
        sgst=float(gst_details["sgst"]),
        igst=float(gst_details["igst"]),
        tds_rate=float(tds_details["tds_rate"]),
        tds_amount=float(tds_details["tds_amount"]),
    )

    try:
        session.add(invoice)
        session.commit()
        session.refresh(invoice)
        log_action(
            session=session,
            user_id=user_id,
            action="CREATE",
            entity_type="Invoice",
            entity_id=invoice.id,
            metadata={
                "invoice_number": invoice.invoice_number,
                "transaction_type": invoice.transaction_type.value,
                "amount": invoice.total_amount,
                "tds_amount": invoice.tds_amount,
            },
        )
        return invoice
    except Exception:
        session.rollback()
        raise


def generate_monthly_gst_summary(session: Session, user_id: int, year_month: str) -> dict:
    period_start = datetime.strptime(year_month, "%Y-%m").date()
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1, day=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1, day=1)

    invoices = (
        session.query(Invoice)
        .filter(
            Invoice.user_id == user_id,
            Invoice.invoice_date >= period_start,
            Invoice.invoice_date < period_end,
        )
        .all()
    )

    total_output_gst = float(
        sum(
            float(invoice.cgst + invoice.sgst + invoice.igst)
            for invoice in invoices
            if invoice.transaction_type == InvoiceTransactionType.SALE
        )
    )
    total_input_gst = float(
        sum(
            float(invoice.cgst + invoice.sgst + invoice.igst)
            for invoice in invoices
            if invoice.transaction_type == InvoiceTransactionType.PURCHASE
        )
    )

    gst_liability = calculate_net_gst_liability(
        output_gst_total=total_output_gst, input_gst_total=total_input_gst
    )
    net_payable = float(gst_liability["net_payable"])

    tax_liability = (
        session.query(TaxLiability)
        .filter(TaxLiability.user_id == user_id, TaxLiability.period_month == year_month)
        .first()
    )

    if tax_liability is None:
        tax_liability = TaxLiability(
            user_id=user_id,
            period_month=year_month,
            total_output_gst=total_output_gst,
            total_input_gst=total_input_gst,
            net_gst_payable=net_payable,
        )
        session.add(tax_liability)
    else:
        tax_liability.total_output_gst = total_output_gst
        tax_liability.total_input_gst = total_input_gst
        tax_liability.net_gst_payable = net_payable

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return {
        "output_gst": total_output_gst,
        "input_gst": total_input_gst,
        "net_payable": net_payable,
    }


def generate_monthly_tds_summary(session: Session, user_id: int, year_month: str) -> dict:
    period_start = datetime.strptime(year_month, "%Y-%m").date()
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1, day=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1, day=1)

    invoices = (
        session.query(Invoice)
        .filter(
            Invoice.user_id == user_id,
            Invoice.invoice_date >= period_start,
            Invoice.invoice_date < period_end,
        )
        .all()
    )

    total_tds_deducted = float(sum(float(invoice.tds_amount or 0.0) for invoice in invoices))

    tds_liability = (
        session.query(TDSLiability)
        .filter(TDSLiability.user_id == user_id, TDSLiability.period_month == year_month)
        .first()
    )

    if tds_liability is None:
        tds_liability = TDSLiability(
            user_id=user_id,
            period_month=year_month,
            total_tds_deducted=total_tds_deducted,
        )
        session.add(tds_liability)
    else:
        tds_liability.total_tds_deducted = total_tds_deducted

    try:
        session.commit()
    except Exception:
        session.rollback()
        raise

    return {"total_tds_deducted": total_tds_deducted}
