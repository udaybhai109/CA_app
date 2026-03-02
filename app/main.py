import json
import os
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from .accounting_engine import generate_balance_sheet, generate_profit_and_loss
from .advisory_agent import generate_advice
from .aging_analysis import calculate_ap_aging, calculate_ar_aging
from .alert_engine import generate_alerts
from .auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    hash_refresh_token,
    require_privileged_user,
    verify_token,
    verify_password,
)
from .database import Base, engine, get_db
from .financial_analysis import calculate_cash_runway, calculate_current_ratio, calculate_net_profit_margin
from .forecasting import (
    forecast_cash_balance,
    forecast_expenses,
    forecast_gst_liability,
    forecast_revenue,
)
from .gst_service import (
    create_invoice_with_gst,
    generate_monthly_gst_summary,
    generate_monthly_tds_summary,
)
from .models import AuditLog, RefreshToken, User
from .period_service import close_period


app = FastAPI(title="AI Accounting Backend")
REFRESH_COOKIE_NAME = "refresh_token"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")

if CORS_ALLOW_ORIGINS == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [origin.strip() for origin in CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvoiceCreateRequest(BaseModel):
    user_id: int
    invoice_number: str
    invoice_date: str
    amount: float
    gst_rate: float
    transaction_type: str
    is_interstate: bool


class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str = "business"


class LoginRequest(BaseModel):
    email: str
    password: str


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.middleware("http")
async def protect_admin_and_bank_routes(request: Request, call_next):
    protected_prefixes = ("/admin", "/bank")
    path = request.url.path

    if path.startswith(protected_prefixes):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing bearer token"},
            )

        token = auth_header.split(" ", 1)[1]
        try:
            payload = verify_token(token)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        if payload.get("role") not in {"ca", "admin"}:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Forbidden: admin or CA role required"},
            )

    return await call_next(request)


@app.get("/")
def root():
    return {"message": "AI-powered accounting backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role or "business",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "email": user.email, "role": user.role}


@app.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token_plain, refresh_expires_at = create_refresh_token()
    refresh_token_hashed = hash_refresh_token(refresh_token_plain)

    db.add(
        RefreshToken(
            user_id=user.id,
            token=refresh_token_hashed,
            expires_at=refresh_expires_at,
        )
    )
    db.commit()

    set_refresh_cookie(response, refresh_token_plain)
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/refresh")
def refresh_access_token(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token_plain = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token_plain:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token cookie"
        )

    refresh_token_hashed = hash_refresh_token(refresh_token_plain)
    stored_token = db.query(RefreshToken).filter(RefreshToken.token == refresh_token_hashed).first()
    if stored_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if stored_token.expires_at < datetime.utcnow():
        db.delete(stored_token)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = db.query(User).filter(User.id == stored_token.user_id).first()
    if user is None:
        db.delete(stored_token)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    db.delete(stored_token)
    new_refresh_plain, new_refresh_expires_at = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token=hash_refresh_token(new_refresh_plain),
            expires_at=new_refresh_expires_at,
        )
    )
    db.commit()

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    set_refresh_cookie(response, new_refresh_plain)
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token_plain = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token_plain:
        refresh_token_hashed = hash_refresh_token(refresh_token_plain)
        db.query(RefreshToken).filter(RefreshToken.token == refresh_token_hashed).delete()
        db.commit()

    clear_refresh_cookie(response)
    return {"message": "Logged out successfully"}


@app.get("/pnl/{user_id}")
def get_profit_and_loss(user_id: int, db: Session = Depends(get_db)):
    return generate_profit_and_loss(db, user_id)


@app.get("/balance-sheet/{user_id}")
def get_balance_sheet(user_id: int, db: Session = Depends(get_db)):
    return generate_balance_sheet(db, user_id)


@app.get("/advice/{user_id}")
def get_advice(user_id: int, question: str, db: Session = Depends(get_db)):
    return generate_advice(db, user_id, question)


@app.post("/invoice")
def create_invoice(payload: InvoiceCreateRequest, db: Session = Depends(get_db)):
    invoice = create_invoice_with_gst(
        session=db,
        user_id=payload.user_id,
        invoice_number=payload.invoice_number,
        invoice_date=payload.invoice_date,
        amount=payload.amount,
        gst_rate=payload.gst_rate,
        transaction_type=payload.transaction_type,
        is_interstate=payload.is_interstate,
    )

    return {
        "id": invoice.id,
        "user_id": invoice.user_id,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "total_amount": invoice.total_amount,
        "gst_rate": invoice.gst_rate,
        "is_interstate": invoice.is_interstate,
        "transaction_type": invoice.transaction_type.value,
        "cgst": invoice.cgst,
        "sgst": invoice.sgst,
        "igst": invoice.igst,
        "created_at": invoice.created_at,
    }


@app.get("/gst-summary/{user_id}/{year_month}")
def get_gst_summary(user_id: int, year_month: str, db: Session = Depends(get_db)):
    return generate_monthly_gst_summary(db, user_id, year_month)


@app.get("/tds-summary/{user_id}/{year_month}")
def get_tds_summary(user_id: int, year_month: str, db: Session = Depends(get_db)):
    return generate_monthly_tds_summary(db, user_id, year_month)


@app.get("/financial-health/{user_id}")
def get_financial_health(user_id: int, db: Session = Depends(get_db)):
    return {
        "current_ratio": calculate_current_ratio(db, user_id),
        "net_profit_margin": calculate_net_profit_margin(db, user_id),
        "cash_runway": calculate_cash_runway(db, user_id),
    }


@app.get("/aging/{user_id}")
def get_aging(user_id: int, db: Session = Depends(get_db)):
    return {
        "accounts_receivable": calculate_ar_aging(db, user_id),
        "accounts_payable": calculate_ap_aging(db, user_id),
    }


@app.get("/alerts/{user_id}")
def get_alerts(user_id: int, db: Session = Depends(get_db)):
    return {"alerts": generate_alerts(db, user_id)}


@app.get("/forecast/{user_id}")
def get_forecast(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: cannot view forecast for another user",
        )

    return {
        "revenue_projection": forecast_revenue(db, user_id),
        "expense_projection": forecast_expenses(db, user_id),
        "cash_projection": forecast_cash_balance(db, user_id),
        "gst_projection": forecast_gst_liability(db, user_id),
    }


@app.post("/close-period/{user_id}/{year_month}")
def close_accounting_period(
    user_id: int,
    year_month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_privileged_user),
):
    if not isinstance(current_user, User):
        fallback_user = db.query(User).filter(User.id == user_id).first()
        if fallback_user is None or fallback_user.role not in {"ca", "admin"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized action")
    elif current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: cannot close period for another user",
        )

    return close_period(db, user_id, year_month)


@app.get("/audit/{user_id}")
def get_audit_logs(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_privileged_user),
):
    if not isinstance(current_user, User):
        fallback_user = db.query(User).filter(User.id == user_id).first()
        if fallback_user is None or fallback_user.role not in {"ca", "admin"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized action")
    elif current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: cannot view audit for another user",
        )

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user_id)
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    return {
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "timestamp": log.timestamp,
                "metadata": json.loads(log.metadata_text) if log.metadata_text else None,
            }
            for log in logs
        ]
    }
