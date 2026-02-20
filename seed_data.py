from app.accounting_engine import create_transaction
from app.database import SessionLocal
from app.models import AccountType, LedgerAccount, User


if __name__ == "__main__":
    session = SessionLocal()
    try:
        user = User(email="test@demo.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        cash_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
        sales_revenue_account = LedgerAccount(
            name="Sales Revenue", account_type=AccountType.REVENUE, user_id=user.id
        )
        office_expense_account = LedgerAccount(
            name="Office Expense", account_type=AccountType.EXPENSE, user_id=user.id
        )
        owner_capital_account = LedgerAccount(
            name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id
        )
        accounts_payable_account = LedgerAccount(
            name="Accounts Payable", account_type=AccountType.LIABILITY, user_id=user.id
        )

        session.add_all(
            [
                cash_account,
                sales_revenue_account,
                office_expense_account,
                owner_capital_account,
                accounts_payable_account,
            ]
        )
        session.commit()
        session.refresh(cash_account)
        session.refresh(sales_revenue_account)
        session.refresh(office_expense_account)
        session.refresh(owner_capital_account)
        session.refresh(accounts_payable_account)

        create_transaction(
            session=session,
            user_id=user.id,
            description="Owner invests into business",
            debit_account_id=cash_account.id,
            credit_account_id=owner_capital_account.id,
            amount=100000.0,
        )
        create_transaction(
            session=session,
            user_id=user.id,
            description="Business earns revenue",
            debit_account_id=cash_account.id,
            credit_account_id=sales_revenue_account.id,
            amount=50000.0,
        )
        create_transaction(
            session=session,
            user_id=user.id,
            description="Business pays office expense",
            debit_account_id=office_expense_account.id,
            credit_account_id=cash_account.id,
            amount=20000.0,
        )

        session.commit()
        print("Seed data inserted successfully")
    finally:
        session.close()
