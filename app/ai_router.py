def route_user_query(query: str) -> str:
    normalized_query = query.lower()

    if "gst" in normalized_query:
        return "COMPLIANCE"
    if "tds" in normalized_query:
        return "COMPLIANCE"
    if "profit" in normalized_query:
        return "ACCOUNTING"
    if "balance sheet" in normalized_query:
        return "ACCOUNTING"

    return "ADVISORY"
