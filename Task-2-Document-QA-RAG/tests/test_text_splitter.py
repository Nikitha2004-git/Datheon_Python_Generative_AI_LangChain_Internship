import pytest
from langchain_core.documents import Document

from app.text_splitter import split_documents


def _page(text, page=1):
    return Document(
        page_content=text, metadata={"source": "a.pdf", "page": page, "file_hash": "h" * 64}
    )


def test_long_text_is_split_into_multiple_chunks():
    chunks = split_documents([_page("word " * 400)], chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 200 for c in chunks)


def test_short_text_stays_one_chunk():
    chunks = split_documents([_page("Short text.")], 1000, 100)
    assert len(chunks) == 1


def test_metadata_is_preserved_and_indexed():
    pages = [_page("alpha " * 100, page=1), _page("beta " * 100, page=2)]
    chunks = split_documents(pages, chunk_size=150, chunk_overlap=10)
    assert {c.metadata["page"] for c in chunks} == {1, 2}
    assert all(c.metadata["source"] == "a.pdf" for c in chunks)
    ids = [c.metadata["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))  # unique ids
    assert [c.metadata["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_overlap_repeats_text_between_neighbours():
    text = " ".join(f"w{i}" for i in range(200))
    chunks = split_documents([_page(text)], chunk_size=100, chunk_overlap=30)
    first_tail = chunks[0].page_content.split()[-1]
    assert first_tail in chunks[1].page_content


@pytest.mark.parametrize("size,overlap", [(0, 0), (100, 100), (100, 150), (100, -1)])
def test_invalid_settings_rejected(size, overlap):
    with pytest.raises(ValueError):
        split_documents([_page("text")], size, overlap)
