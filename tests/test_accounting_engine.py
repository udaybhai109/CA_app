from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.accounting_engine import (
    create_transaction,
    generate_balance_sheet,
    generate_profit_and_loss,
)
from app.database import Base
from app.models import AccountType, JournalEntry, LedgerAccount, Transaction, User


def build_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def seed_user_and_accounts(session):
    user = User(email="user@example.com")
    session.add(user)
    session.flush()

    debit_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    credit_account = LedgerAccount(
        name="Service Revenue", account_type=AccountType.REVENUE, user_id=user.id
    )
    session.add_all([debit_account, credit_account])
    session.commit()
    return user, debit_account, credit_account


def test_debit_equals_credit():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    user, debit_account, credit_account = seed_user_and_accounts(session)

    transaction = create_transaction(
        session=session,
        user_id=user.id,
        description="Invoice payment",
        debit_account_id=debit_account.id,
        credit_account_id=credit_account.id,
        amount=250.75,
    )

    entries = session.query(JournalEntry).filter_by(transaction_id=transaction.id).all()
    total_debit = sum(entry.debit_amount for entry in entries)
    total_credit = sum(entry.credit_amount for entry in entries)

    assert len(entries) == 2
    assert total_debit == total_credit


def test_no_math_mistakes_in_entries():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    user, debit_account, credit_account = seed_user_and_accounts(session)

    transaction = create_transaction(
        session=session,
        user_id=user.id,
        description="Office expense",
        debit_account_id=debit_account.id,
        credit_account_id=credit_account.id,
        amount=100.0,
    )

    entries = session.query(JournalEntry).filter_by(transaction_id=transaction.id).all()
    debit_entry = next(entry for entry in entries if entry.debit_amount > 0)
    credit_entry = next(entry for entry in entries if entry.credit_amount > 0)

    assert debit_entry.debit_amount == 100.0
    assert debit_entry.credit_amount == 0.0
    assert credit_entry.credit_amount == 100.0
    assert credit_entry.debit_amount == 0.0


def test_proper_commit_logic():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    user, debit_account, credit_account = seed_user_and_accounts(session)
    user_id = user.id
    debit_account_id = debit_account.id
    credit_account_id = credit_account.id

    create_transaction(
        session=session,
        user_id=user_id,
        description="Committed transaction",
        debit_account_id=debit_account_id,
        credit_account_id=credit_account_id,
        amount=99.99,
    )
    session.close()

    verify_session = SessionLocal()
    assert verify_session.query(Transaction).count() == 1
    assert verify_session.query(JournalEntry).count() == 2

    try:
        create_transaction(
            session=verify_session,
            user_id=user_id,
            description="Should fail",
            debit_account_id=debit_account_id,
            credit_account_id=credit_account_id,
            amount=0,
        )
    except ValueError:
        pass
    else:
        assert False, "Expected ValueError for non-positive amount"

    assert verify_session.query(Transaction).count() == 1
    assert verify_session.query(JournalEntry).count() == 2


def seed_user_for_pnl(session):
    user = User(email="pnl_user@example.com")
    session.add(user)
    session.flush()

    cash_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    revenue_account = LedgerAccount(
        name="Service Revenue", account_type=AccountType.REVENUE, user_id=user.id
    )
    expense_account = LedgerAccount(
        name="Rent Expense", account_type=AccountType.EXPENSE, user_id=user.id
    )
    session.add_all([cash_account, revenue_account, expense_account])
    session.commit()

    return user, cash_account, revenue_account, expense_account


def create_sample_pnl_data(session, user_id, cash_account_id, revenue_account_id, expense_account_id):
    create_transaction(
        session=session,
        user_id=user_id,
        description="Revenue recognized",
        debit_account_id=cash_account_id,
        credit_account_id=revenue_account_id,
        amount=1000.0,
    )
    create_transaction(
        session=session,
        user_id=user_id,
        description="Revenue reversal",
        debit_account_id=revenue_account_id,
        credit_account_id=cash_account_id,
        amount=100.0,
    )
    create_transaction(
        session=session,
        user_id=user_id,
        description="Expense booked",
        debit_account_id=expense_account_id,
        credit_account_id=cash_account_id,
        amount=300.0,
    )
    create_transaction(
        session=session,
        user_id=user_id,
        description="Expense reversal",
        debit_account_id=cash_account_id,
        credit_account_id=expense_account_id,
        amount=50.0,
    )


def test_revenue_logic_correct():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    user, cash_account, revenue_account, expense_account = seed_user_for_pnl(session)
    create_sample_pnl_data(
        session,
        user.id,
        cash_account.id,
        revenue_account.id,
        expense_account.id,
    )

    pnl = generate_profit_and_loss(session, user.id)

    assert pnl["revenues"]["Service Revenue"] == 900.0
    assert pnl["total_revenue"] == 900.0


def test_expense_logic_correct():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    user, cash_account, revenue_account, expense_account = seed_user_for_pnl(session)
    create_sample_pnl_data(
        session,
        user.id,
        cash_account.id,
        revenue_account.id,
        expense_account.id,
    )

    pnl = generate_profit_and_loss(session, user.id)

    assert pnl["expenses"]["Rent Expense"] == 250.0
    assert pnl["total_expenses"] == 250.0


def test_net_profit_equals_revenue_minus_expenses():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    user, cash_account, revenue_account, expense_account = seed_user_for_pnl(session)
    create_sample_pnl_data(
        session,
        user.id,
        cash_account.id,
        revenue_account.id,
        expense_account.id,
    )

    pnl = generate_profit_and_loss(session, user.id)

    assert pnl["net_profit"] == pnl["total_revenue"] - pnl["total_expenses"]
    assert pnl["net_profit"] == 650.0


def seed_user_for_balance_sheet(session):
    user = User(email="balance_sheet_user@example.com")
    session.add(user)
    session.flush()

    cash_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    equipment_account = LedgerAccount(
        name="Equipment", account_type=AccountType.ASSET, user_id=user.id
    )
    loan_payable_account = LedgerAccount(
        name="Loan Payable", account_type=AccountType.LIABILITY, user_id=user.id
    )
    owner_capital_account = LedgerAccount(
        name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id
    )
    session.add_all([cash_account, equipment_account, loan_payable_account, owner_capital_account])
    session.commit()

    return user, cash_account, equipment_account, loan_payable_account, owner_capital_account


def create_sample_balance_sheet_data(
    session,
    user_id,
    cash_account_id,
    equipment_account_id,
    loan_payable_account_id,
    owner_capital_account_id,
):
    create_transaction(
        session=session,
        user_id=user_id,
        description="Owner investment",
        debit_account_id=cash_account_id,
        credit_account_id=owner_capital_account_id,
        amount=1000.0,
    )
    create_transaction(
        session=session,
        user_id=user_id,
        description="Loan received",
        debit_account_id=cash_account_id,
        credit_account_id=loan_payable_account_id,
        amount=500.0,
    )
    create_transaction(
        session=session,
        user_id=user_id,
        description="Equipment purchase",
        debit_account_id=equipment_account_id,
        credit_account_id=cash_account_id,
        amount=300.0,
    )


def test_balance_sheet_equation_holds():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    (
        user,
        cash_account,
        equipment_account,
        loan_payable_account,
        owner_capital_account,
    ) = seed_user_for_balance_sheet(session)
    create_sample_balance_sheet_data(
        session=session,
        user_id=user.id,
        cash_account_id=cash_account.id,
        equipment_account_id=equipment_account.id,
        loan_payable_account_id=loan_payable_account.id,
        owner_capital_account_id=owner_capital_account.id,
    )

    balance_sheet = generate_balance_sheet(session, user.id)

    assert balance_sheet["total_assets"] == (
        balance_sheet["total_liabilities"] + balance_sheet["total_equity"]
    )


def test_balance_sheet_totals_are_exact():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    (
        user,
        cash_account,
        equipment_account,
        loan_payable_account,
        owner_capital_account,
    ) = seed_user_for_balance_sheet(session)
    create_sample_balance_sheet_data(
        session=session,
        user_id=user.id,
        cash_account_id=cash_account.id,
        equipment_account_id=equipment_account.id,
        loan_payable_account_id=loan_payable_account.id,
        owner_capital_account_id=owner_capital_account.id,
    )

    balance_sheet = generate_balance_sheet(session, user.id)

    assert balance_sheet["assets"]["Cash"] == 1200.0
    assert balance_sheet["assets"]["Equipment"] == 300.0
    assert balance_sheet["liabilities"]["Loan Payable"] == 500.0
    assert balance_sheet["equity"]["Owner Capital"] == 1000.0
    assert balance_sheet["total_assets"] == 1500.0
    assert balance_sheet["total_liabilities"] == 500.0
    assert balance_sheet["total_equity"] == 1000.0


def test_balance_sheet_manual_entries_balanced():
    SessionLocal = build_session_factory()
    session = SessionLocal()

    user = User(email="manual_balanced_user@example.com")
    session.add(user)
    session.flush()

    cash_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    loan_account = LedgerAccount(
        name="Loan Payable", account_type=AccountType.LIABILITY, user_id=user.id
    )
    capital_account = LedgerAccount(
        name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id
    )
    session.add_all([cash_account, loan_account, capital_account])
    session.flush()

    t1 = Transaction(user_id=user.id, description="Owner investment", date=date.today())
    t2 = Transaction(user_id=user.id, description="Loan received", date=date.today())
    session.add_all([t1, t2])
    session.flush()

    session.add_all(
        [
            JournalEntry(
                transaction_id=t1.id,
                ledger_account_id=cash_account.id,
                debit_amount=200.0,
                credit_amount=0.0,
            ),
            JournalEntry(
                transaction_id=t1.id,
                ledger_account_id=capital_account.id,
                debit_amount=0.0,
                credit_amount=200.0,
            ),
            JournalEntry(
                transaction_id=t2.id,
                ledger_account_id=cash_account.id,
                debit_amount=100.0,
                credit_amount=0.0,
            ),
            JournalEntry(
                transaction_id=t2.id,
                ledger_account_id=loan_account.id,
                debit_amount=0.0,
                credit_amount=100.0,
            ),
        ]
    )
    session.commit()

    balance_sheet = generate_balance_sheet(session, user.id)
    assert balance_sheet["total_assets"] == 300.0
    assert balance_sheet["total_liabilities"] == 100.0
    assert balance_sheet["total_equity"] == 200.0


def test_balance_sheet_manual_entries_unbalanced_raises():
    SessionLocal = build_session_factory()
    session = SessionLocal()

    user = User(email="manual_unbalanced_user@example.com")
    session.add(user)
    session.flush()

    cash_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    session.add(cash_account)
    session.flush()

    transaction = Transaction(user_id=user.id, description="Broken entry", date=date.today())
    session.add(transaction)
    session.flush()

    session.add(
        JournalEntry(
            transaction_id=transaction.id,
            ledger_account_id=cash_account.id,
            debit_amount=150.0,
            credit_amount=0.0,
        )
    )
    session.commit()

    with pytest.raises(Exception, match="Balance Sheet Not Balanced"):
        generate_balance_sheet(session, user.id)


def test_balance_sheet_does_not_double_count_revenue_accounts():
    SessionLocal = build_session_factory()
    session = SessionLocal()

    user = User(email="no_double_count_user@example.com")
    session.add(user)
    session.flush()

    cash_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    revenue_account = LedgerAccount(
        name="Service Revenue", account_type=AccountType.REVENUE, user_id=user.id
    )
    expense_account = LedgerAccount(
        name="Rent Expense", account_type=AccountType.EXPENSE, user_id=user.id
    )
    owner_capital_account = LedgerAccount(
        name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id
    )
    session.add_all([cash_account, revenue_account, expense_account, owner_capital_account])
    session.commit()

    create_transaction(
        session=session,
        user_id=user.id,
        description="Initial capital",
        debit_account_id=cash_account.id,
        credit_account_id=owner_capital_account.id,
        amount=1000.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Revenue transaction",
        debit_account_id=cash_account.id,
        credit_account_id=revenue_account.id,
        amount=400.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Expense transaction",
        debit_account_id=expense_account.id,
        credit_account_id=cash_account.id,
        amount=150.0,
    )

    balance_sheet = generate_balance_sheet(session, user.id)

    assert "Service Revenue" not in balance_sheet["assets"]
    assert "Service Revenue" not in balance_sheet["liabilities"]
    assert "Service Revenue" not in balance_sheet["equity"]
    assert balance_sheet["equity"]["Retained Earnings"] == 250.0
    assert balance_sheet["total_assets"] == 1250.0
    assert balance_sheet["total_liabilities"] == 0.0
    assert balance_sheet["total_equity"] == 1250.0


def test_retained_earnings_adjustment_is_reporting_only_without_db_mutation():
    SessionLocal = build_session_factory()
    session = SessionLocal()

    user = User(email="reporting_only_re_user@example.com")
    session.add(user)
    session.flush()

    cash_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    revenue_account = LedgerAccount(
        name="Service Revenue", account_type=AccountType.REVENUE, user_id=user.id
    )
    session.add_all([cash_account, revenue_account])
    session.commit()

    before_count = (
        session.query(LedgerAccount)
        .filter(
            LedgerAccount.name == "Retained Earnings",
            LedgerAccount.account_type == AccountType.EQUITY,
            LedgerAccount.user_id == user.id,
        )
        .count()
    )

    create_transaction(
        session=session,
        user_id=user.id,
        description="Revenue only",
        debit_account_id=cash_account.id,
        credit_account_id=revenue_account.id,
        amount=500.0,
    )

    balance_sheet = generate_balance_sheet(session, user.id)

    after_count = (
        session.query(LedgerAccount)
        .filter(
            LedgerAccount.name == "Retained Earnings",
            LedgerAccount.account_type == AccountType.EQUITY,
            LedgerAccount.user_id == user.id,
        )
        .count()
    )

    assert before_count == 0
    assert after_count == 0
    assert balance_sheet["equity"]["Retained Earnings"] == 500.0
    assert balance_sheet["total_assets"] == 500.0
    assert balance_sheet["total_equity"] == 500.0
