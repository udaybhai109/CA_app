from datetime import date
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import AccountType, JournalEntry, LedgerAccount, Transaction


def calculate_total_balance(entries: Iterable[JournalEntry]) -> float:
    return float(sum(entry.debit_amount - entry.credit_amount for entry in entries))


def create_transaction(
    session: Session,
    user_id: int,
    description: str,
    debit_account_id: int,
    credit_account_id: int,
    amount: float,
) -> Transaction:
    if amount <= 0:
        raise ValueError("Amount must be greater than 0.")

    transaction = Transaction(user_id=user_id, description=description, date=date.today())

    try:
        session.add(transaction)
        session.flush()

        debit_entry = JournalEntry(
            transaction_id=transaction.id,
            ledger_account_id=debit_account_id,
            debit_amount=float(amount),
            credit_amount=0.0,
        )
        credit_entry = JournalEntry(
            transaction_id=transaction.id,
            ledger_account_id=credit_account_id,
            debit_amount=0.0,
            credit_amount=float(amount),
        )

        session.add_all([debit_entry, credit_entry])
        session.commit()
        session.refresh(transaction)
        return transaction
    except Exception:
        session.rollback()
        raise


def generate_profit_and_loss(session: Session, user_id: int) -> dict:
    rows = (
        session.query(
            LedgerAccount.name,
            LedgerAccount.account_type,
            func.coalesce(func.sum(JournalEntry.debit_amount), 0.0).label("total_debit"),
            func.coalesce(func.sum(JournalEntry.credit_amount), 0.0).label("total_credit"),
        )
        .outerjoin(JournalEntry, JournalEntry.ledger_account_id == LedgerAccount.id)
        .filter(
            LedgerAccount.user_id == user_id,
            LedgerAccount.account_type.in_([AccountType.REVENUE, AccountType.EXPENSE]),
        )
        .group_by(LedgerAccount.id, LedgerAccount.name, LedgerAccount.account_type)
        .all()
    )

    revenues: dict[str, float] = {}
    expenses: dict[str, float] = {}
    total_revenue = 0.0
    total_expenses = 0.0

    for account_name, account_type, total_debit, total_credit in rows:
        debit_value = float(total_debit or 0.0)
        credit_value = float(total_credit or 0.0)

        if account_type == AccountType.REVENUE:
            net = credit_value - debit_value
            revenues[account_name] = net
            total_revenue += net
        elif account_type == AccountType.EXPENSE:
            net = debit_value - credit_value
            expenses[account_name] = net
            total_expenses += net

    net_profit = total_revenue - total_expenses

    return {
        "revenues": revenues,
        "expenses": expenses,
        "total_revenue": float(total_revenue),
        "total_expenses": float(total_expenses),
        "net_profit": float(net_profit),
    }


def generate_balance_sheet(session: Session, user_id: int) -> dict:
    pnl = generate_profit_and_loss(session, user_id)
    net_profit = float(pnl.get("net_profit", 0.0))

    rows = (
        session.query(
            LedgerAccount.name,
            LedgerAccount.account_type,
            func.coalesce(func.sum(JournalEntry.debit_amount), 0.0).label("total_debit"),
            func.coalesce(func.sum(JournalEntry.credit_amount), 0.0).label("total_credit"),
        )
        .outerjoin(JournalEntry, JournalEntry.ledger_account_id == LedgerAccount.id)
        .filter(
            LedgerAccount.user_id == user_id,
            LedgerAccount.account_type.in_(
                [AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY]
            ),
        )
        .group_by(LedgerAccount.id, LedgerAccount.name, LedgerAccount.account_type)
        .all()
    )

    assets: dict[str, float] = {}
    liabilities: dict[str, float] = {}
    equity: dict[str, float] = {}
    total_assets = 0.0
    total_liabilities = 0.0
    total_equity = 0.0

    for account_name, account_type, total_debit, total_credit in rows:
        debit_value = float(total_debit or 0.0)
        credit_value = float(total_credit or 0.0)

        if account_type == AccountType.ASSET:
            balance = debit_value - credit_value
            assets[account_name] = balance
            total_assets += balance
        elif account_type == AccountType.LIABILITY:
            balance = credit_value - debit_value
            liabilities[account_name] = balance
            total_liabilities += balance
        elif account_type == AccountType.EQUITY:
            balance = credit_value - debit_value
            equity[account_name] = balance
            total_equity += balance

    existing_retained_earnings = float(equity.get("Retained Earnings", 0.0))
    equity["Retained Earnings"] = net_profit
    total_equity = float(total_equity - existing_retained_earnings + net_profit)

    if total_assets != (total_liabilities + total_equity):
        raise Exception("Balance Sheet Not Balanced")

    return {
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": float(total_assets),
        "total_liabilities": float(total_liabilities),
        "total_equity": float(total_equity),
    }
