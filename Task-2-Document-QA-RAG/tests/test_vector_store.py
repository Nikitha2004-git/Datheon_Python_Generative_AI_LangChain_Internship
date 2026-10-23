from langchain_core.documents import Document

from app.ingestion import ingest_file
from app.retriever import retrieve
from app.vector_store import SessionVectorStore

MAX = 1024 * 1024


def _ingest(store, name, data):
    return ingest_file(store, name, data, MAX, 300, 30)


def test_ingest_and_retrieve_relevant_chunk(store):
    _ingest(store, "solar.txt", b"Solar panels convert sunlight into electricity for homes.")
    _ingest(store, "cooking.txt", b"Bake the bread at high heat until the crust turns golden.")
    results = retrieve(store, "How do solar panels make electricity?", top_k=1)
    assert len(results) == 1
    assert results[0].source == "solar.txt"
    assert results[0].page is None


def test_pdf_page_numbers_survive_retrieval(store, pdf_bytes):
    _ingest(store, "energy.pdf", pdf_bytes)
    top = retrieve(store, "wind turbines moving air", top_k=1)[0]
    assert top.source == "energy.pdf"
    assert top.page == 2
    assert top.label == "energy.pdf (page 2)"


def test_top_k_limits_results(store):
    _ingest(store, "a.txt", ("Paragraph about topic. " * 80).encode())
    assert len(retrieve(store, "topic", top_k=2)) == 2


def test_empty_store_returns_no_results(store):
    assert store.count() == 0
    assert retrieve(store, "anything", top_k=4) == []


def test_blank_question_returns_no_results(store):
    _ingest(store, "a.txt", b"Some content here.")
    assert retrieve(store, "   ", top_k=4) == []


def test_same_file_is_not_embedded_twice(store):
    first = _ingest(store, "a.txt", b"Unique content for dedupe test.")
    count = store.count()
    second = _ingest(store, "renamed.txt", b"Unique content for dedupe test.")
    assert first.status == "added"
    assert second.status == "skipped"
    assert store.count() == count


def test_bad_files_return_error_status_not_exception(store):
    assert _ingest(store, "x.docx", b"data").status == "error"
    assert _ingest(store, "e.txt", b"").status == "error"
    assert _ingest(store, "bad.pdf", b"%PDF-garbage").status == "error"
    assert store.count() == 0


def test_remove_file_only_removes_that_file(store):
    a = _ingest(store, "a.txt", b"Apples are red fruit.")
    _ingest(store, "b.txt", b"Bananas are yellow fruit.")
    store.remove_file(a.file_hash)
    sources = {r.source for r in retrieve(store, "fruit", top_k=5)}
    assert sources == {"b.txt"}


def test_clear_really_empties_the_collection(store):
    _ingest(store, "a.txt", b"Some stored content.")
    assert store.count() > 0
    store.clear()
    assert store.count() == 0
    assert retrieve(store, "stored content", top_k=3) == []
    # and the store is usable again after clearing
    assert _ingest(store, "a.txt", b"Some stored content.").status == "added"


def test_sessions_are_isolated(tmp_path, embeddings):
    path = tmp_path / "shared_dir"
    one = SessionVectorStore("sessionone", embeddings, path)
    two = SessionVectorStore("sessiontwo", embeddings, path)
    try:
        _ingest(one, "secret.txt", b"The launch code is banana.")
        assert retrieve(two, "launch code banana", top_k=3) == []
        assert len(retrieve(one, "launch code banana", top_k=3)) == 1
        two.clear()  # clearing session two must not touch session one
        assert one.count() > 0
    finally:
        one.delete_permanently()
        two.delete_permanently()


def test_none_metadata_is_accepted(store):
    chunk = Document(
        page_content="text",
        metadata={"source": "a.txt", "page": None, "file_hash": "abc", "chunk_id": "abc-0"},
    )
    assert store.add_file_chunks("abc", [chunk]) == 1
