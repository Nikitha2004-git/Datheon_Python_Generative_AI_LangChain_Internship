# Interview questions and simple answers

**1. What does your project do?**
It lets a user upload PDF/TXT files and ask questions. The app finds the most relevant
parts of the documents and asks Gemini to answer only from them, then shows the sources.

**2. What is RAG and why use it instead of just asking the LLM?**
RAG retrieves relevant text first and gives it to the LLM. The model has not seen private
documents and may hallucinate; RAG gives it evidence and lets us show sources.

**3. Difference between an LLM, an embedding model, a vector database and a retriever?**
LLM writes text. Embedding model converts text to numbers that represent meaning. Vector
database stores those numbers and finds nearest ones. Retriever is the logic that embeds the
question, queries the database, and returns the best chunks.

**4. What is a chunk and why overlap?**
A chunk is a small piece of a document (1000 characters here). Overlap (150) repeats the end of
one chunk at the start of the next so sentences cut at a boundary are not lost.

**5. How did you choose chunk size?**
Started with 1000/150 as a balanced default, made it configurable. Small chunks lose context,
large chunks blur topics and cost more tokens. It can be tuned by testing real questions.

**6. What is an embedding?**
A list of numbers (384 for MiniLM) where similar meanings give nearby vectors.

**7. How is similarity measured?**
Cosine distance between vectors. Chroma returns the K smallest distances.

**8. How do you stop hallucinations?**
Only retrieved text is sent; the prompt says to use only it and to answer `INSUFFICIENT_CONTEXT`
otherwise; temperature is 0; sources come from retrieval metadata. This reduces but cannot
guarantee zero hallucination.

**9. What happens if the answer is not in the documents?**
The model returns the marker, and the app shows "I couldn't find enough information..." and
labels the passages as the closest ones found.

**10. How do you keep users' documents separate?**
Every session gets its own Chroma collection name. Clearing deletes that collection.

**11. How do you avoid re-embedding the same file?**
A SHA-256 hash of the file bytes is stored in each chunk's metadata; if it exists, the file is skipped.

**12. Why local embeddings?**
No cost, no rate limits, works offline after the first download, and document text is not sent
to an API just to be embedded. (It is still sent to Gemini at answer time.)

**13. What privacy issues exist?**
Questions and retrieved chunks go to Google. Free-tier data may be used by Google to improve products.
Local vectors are unencrypted. The API key lives only in `.env`, which is git-ignored.

**14. How do you handle errors?**
Custom exceptions and `translate_llm_error` map status codes (429 rate limit, 401/403 key,
404 model, 5xx outage, network) to short messages. Bad files return an error status per file.

**15. How did you test without paying for API calls?**
Dependency injection: tests pass a fake embedding class and LangChain's fake chat model.
60 tests cover loading, splitting, retrieval, isolation, reset, errors and prompts.

**16. Limits of this project?**
No OCR, no chat memory in retrieval, poor with complex tables, no similarity threshold,
whole-document summaries are weak because only K chunks are used.

**17. How would you improve it?**
Add OCR, hybrid search, reranking, conversation-aware query rewriting, streaming, DOCX support, evaluation sets.

**18. Why Streamlit?**
Fast to build a clean data-app UI in pure Python; `st.session_state` holds per-user state.

**19. What is a virtual environment?**
An isolated Python installation folder per project so dependency versions do not clash.

**20. What is a prompt injection?**
Text in a document that tries to give the model new instructions. The prompt says document
text is data, but this is a mitigation, not a guarantee.
