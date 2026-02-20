import app.rag_engine as rag_engine_module


def test_query_tax_law_returns_top_two_documents():
    result = rag_engine_module.query_tax_law("Explain GST slabs and ITC")

    assert isinstance(result, list)
    assert len(result) == 2
    joined = " ".join(result)
    assert "GST standard slabs" in joined or "Input Tax Credit" in joined


def test_query_tax_law_fallback_path_without_chroma(monkeypatch):
    monkeypatch.setattr(rag_engine_module, "_collection", None)

    result = rag_engine_module.query_tax_law("professional services tds")

    assert isinstance(result, list)
    assert len(result) == 2
    assert any("194J" in doc or "10%" in doc for doc in result)
