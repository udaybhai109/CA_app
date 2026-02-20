from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_file(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_api_and_auth_use_next_public_api_env():
    api_text = read_file("lib/api.ts")
    auth_text = read_file("lib/auth.ts")

    assert "process.env.NEXT_PUBLIC_API" in api_text
    assert "process.env.NEXT_PUBLIC_API" in auth_text


def test_frontend_has_no_hardcoded_localhost_urls():
    frontend_dirs = ["components", "pages", "lib", "context"]

    for directory in frontend_dirs:
        for file_path in (PROJECT_ROOT / directory).rglob("*"):
            if file_path.suffix not in {".ts", ".tsx", ".js", ".jsx"}:
                continue
            content = file_path.read_text(encoding="utf-8")
            assert "localhost" not in content, f"Hardcoded localhost found in {file_path}"
            assert "127.0.0.1" not in content, f"Hardcoded loopback found in {file_path}"


def test_lib_api_contains_required_data_functions():
    api_text = read_file("lib/api.ts")
    required_signatures = [
        "getFinancialHealth",
        "getGstSummary",
        "getAlerts",
        "getPnl",
        "getBalanceSheet",
    ]
    required_paths = [
        "/financial-health/",
        "/gst-summary/",
        "/alerts/",
        "/pnl/",
        "/balance-sheet/",
    ]

    for signature in required_signatures:
        assert signature in api_text
    for api_path in required_paths:
        assert api_path in api_text
    assert "return response.data" in api_text


def test_dashboard_index_calls_required_api_helpers():
    index_text = read_file("pages/index.tsx")

    assert "getFinancialHealth(1)" in index_text
    assert "getGstSummary(1, currentMonth)" in index_text
    assert "getPnl(1)" in index_text
    assert "getBalanceSheet(1)" in index_text
    assert "getAlerts(1)" in index_text
    assert 'balanceSheet?.assets?.["Cash"]' in index_text
    assert "pnl?.net_profit" in index_text
    assert "gstSummary?.net_payable" in index_text
    assert "financialHealth?.cash_runway" in index_text


def test_ai_chat_calls_advice_endpoint_with_question_param():
    chat_text = read_file("components/AIChat.tsx")

    assert "/advice/" in chat_text
    assert "params: { question: trimmedQuestion }" in chat_text
    assert "Analysis based on:" in chat_text


def test_app_layout_wraps_sidebar_and_auth_provider():
    app_text = read_file("pages/_app.tsx")

    assert "AuthProvider" in app_text
    assert "<Sidebar />" in app_text
    assert "ml-[240px]" in app_text
    assert "bg-bg" in app_text


def test_next_middleware_protects_routes_and_redirects_to_login():
    middleware_text = read_file("middleware.ts")

    assert "is_authenticated" in middleware_text
    assert 'new URL("/login", request.url)' in middleware_text
    assert "NextResponse.redirect" in middleware_text
    assert "_next/static" in middleware_text
