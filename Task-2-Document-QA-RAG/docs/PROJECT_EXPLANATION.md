# Project explanation - file by file

## Data flow in one line
`main.py` -> `ingestion.py` (`document_loader` -> `text_splitter` -> `vector_store`/`embeddings`)
and later `main.py` -> `rag_chain.py` (`retriever` -> `prompts` -> Gemini).

## app/

**config.py** - Loads `.env` with python-dotenv into a frozen `Settings` object.
Bad numbers fall back to defaults; overlap is forced smaller than chunk size.
`has_api_key` is false for empty or placeholder keys. No secret is ever printed.

**utils.py** - Custom exceptions (`DocumentLoadError`, `ConfigurationError`,
`AnswerGenerationError`) so the UI can show friendly messages; `file_hash` (SHA-256 of
file bytes, used to avoid re-embedding); session id and Chroma collection naming.

**document_loader.py** - `validate_upload` checks extension, empty, size.
`load_file` reads TXT (tries UTF-8, UTF-16 with BOM, Windows-1252, Latin-1; rejects
binary) or PDF with pypdf (one LangChain `Document` per page with `source`, `page`,
`file_hash`). Corrupted, password-protected and text-less (scanned) PDFs raise clear errors.

**text_splitter.py** - Wraps `RecursiveCharacterTextSplitter`. It tries to split on
paragraphs, then lines, then sentences, then words. Adds `chunk_index` and a unique `chunk_id`.

**embeddings.py** - Loads the local HuggingFace/sentence-transformers model once
(cached). Wraps load failures in a friendly error.

**vector_store.py** - `SessionVectorStore`: one Chroma collection per session
(`session_<id>`), cosine distance. Methods: `has_file`, `add_file_chunks` (skips known
files), `search`, `remove_file`, `clear` (deletes the collection), `count`.
Chroma cannot store `None`, so empty metadata values are dropped.
`purge_persist_directory` is used by `python run.py --clean`.

**retriever.py** - Calls `store.search` and returns `RetrievedChunk` objects
(text, source, page, distance), best first. Empty store or blank question -> empty list.

**ingestion.py** - `ingest_file` runs load -> duplicate check -> split -> embed/store
and always returns an `IngestResult` (added / skipped / error) instead of crashing.

**prompts.py** - System rules, user template, the `INSUFFICIENT_CONTEXT` marker,
and `format_context` which numbers chunks `[1]`, `[2]`... with their source labels.

**rag_chain.py** - `RAGPipeline.ask`: no documents -> message (no API call);
retrieve; build messages; call the model; map any exception to a friendly
`AnswerGenerationError` (`translate_llm_error`); detect "insufficient" replies; find
which `[n]` citations are valid. `build_llm` creates `ChatGoogleGenerativeAI` and
refuses to run without a key. The model is passed in, which is why tests can use a fake one.

**main.py** - The Streamlit page: sidebar (upload, process, file list, remove, reset,
settings), chat area, source expanders, privacy note, setup banner. State lives in
`st.session_state`. It contains no document-processing logic.

## Other files
- **run.py** - `python run.py` starts Streamlit; `--check` prints setup info (no secrets); `--clean` deletes stored vectors.
- **tests/** - `conftest.py` has a fake embedder and PDF builder; each `test_*.py` covers one module.
- **.env.example / .gitignore / requirements.txt / pytest.ini** - configuration.
- **sample_documents/** - three small original text files plus example questions.

## Design decisions worth mentioning
- Local embeddings: free, offline after first download, document text not sent for embedding.
- Per-session collections: prevents documents from different users/sessions mixing.
- Hash-based dedupe: re-uploading the same file does not re-embed it.
- Sources built from retrieved metadata, not model output: no invented citations.
- Everything external (embedding model, Gemini) is injectable: fast offline tests.
