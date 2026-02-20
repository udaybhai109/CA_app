from app.rag_engine import query_tax_law


def test_query_tax_law_tds():
    result = query_tax_law("What is TDS for professional services?")
    joined = " ".join(result)
    assert "194J" in joined or "10%" in joined
