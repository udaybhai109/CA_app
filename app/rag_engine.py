import hashlib

try:
    import chromadb
except Exception:  # pragma: no cover - environment-specific import failure
    chromadb = None


_client = chromadb.EphemeralClient() if chromadb is not None else None
_collection = _client.get_or_create_collection(name="tax_law") if _client is not None else None

_DOCS = [
    "Section 194J: TDS at 10% on professional services exceeding 30000 INR.",
    "GST standard slabs in India include 5%, 12%, 18%, and 28%.",
    "Input Tax Credit can be claimed on purchases used for business purposes.",
]
_DOC_IDS = ["tax_law_1", "tax_law_2", "tax_law_3"]


def _embed_text(text: str, dim: int = 32) -> list[float]:
    vector = [0.0] * dim
    for raw_token in text.lower().split():
        token = raw_token.strip(".,:%()[]{}!?")
        if not token:
            continue
        token_hash = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
        vector[token_hash % dim] += 1.0
    return vector


def initialize_tax_law():
    if _collection is None:
        return

    embeddings = [_embed_text(doc) for doc in _DOCS]
    _collection.upsert(ids=_DOC_IDS, documents=_DOCS, embeddings=embeddings)


def query_tax_law(question: str):
    if _collection is not None:
        initialize_tax_law()
        result = _collection.query(
            query_embeddings=[_embed_text(question)],
            n_results=2,
            include=["documents"],
        )
        documents = result.get("documents", [[]])
        return list(documents[0]) if documents else []

    question_tokens = set(question.lower().split())
    scored_docs = []
    for doc in _DOCS:
        doc_tokens = set(doc.lower().split())
        overlap = len(question_tokens.intersection(doc_tokens))
        scored_docs.append((overlap, doc))
    scored_docs.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored_docs[:2]]
