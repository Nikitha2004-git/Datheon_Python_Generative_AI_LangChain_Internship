# RAG explained (for beginners)

## The problem
A language model (LLM) like Gemini knows a lot, but it has never seen **your**
PDF. If you ask it about your document it may guess, and guesses that sound
confident are called *hallucinations*.

## The idea of RAG
**R**etrieval-**A**ugmented **G**eneration = *look up first, then answer*.

Think of an open-book exam. You do not memorise the book. You find the right
page, read it, then write your answer from that page. RAG does the same.

## Key words, with examples

**Chunk** - a small piece of the document. A 50-page PDF is too big to send to a
model for every question, so we cut it into pieces of about 1000 characters.
*Overlap* means neighbouring chunks share about 150 characters so a sentence
cut at the border still appears whole in one chunk.

**Embedding** - a list of numbers that captures the *meaning* of text.
"How many vacation days do I get?" and "Annual leave entitlement is 18 days"
use different words but get similar numbers, because the meaning is similar.
The numbers come from an *embedding model* (we use `all-MiniLM-L6-v2`, 384 numbers per text).

**Vector database (ChromaDB)** - a database built to store embeddings and quickly
answer: "which stored vectors are closest to this one?" It also keeps the original
text and metadata (filename, page) next to each vector.

**Retriever** - the step that takes your question, embeds it, asks the vector
database for the closest chunks, and returns the top K (default 4).

**Distance** - how far apart two vectors are. We use *cosine distance*:
0 means same direction (very similar meaning), larger is less similar.

**Prompt** - the text we send to the LLM. Ours has rules ("use only the context"),
the numbered chunks, and your question.

**Grounding** - forcing answers to rest on supplied evidence. We do it by
(1) only giving the model retrieved text, (2) telling it to reply `INSUFFICIENT_CONTEXT`
when the text does not contain the answer, and (3) building the source list from
real retrieved metadata, never from what the model says.

## LLM vs embedding model vs vector database vs retriever

| Thing | Job | In this project |
|-------|-----|-----------------|
| LLM | Reads text and writes an answer | Gemini (online, API key) |
| Embedding model | Turns text into vectors | MiniLM (local) |
| Vector database | Stores vectors, finds nearest ones | ChromaDB |
| Retriever | The logic "question in, best chunks out" | `app/retriever.py` |

## Worked example
Documents: `company_leave_policy.txt`. Question: *"How many days of annual leave do I get?"*

1. Question becomes numbers.
2. Chroma returns the chunk starting "1. Annual leave - Every full-time employee receives 18 days..." as closest.
3. Prompt to Gemini: rules + `[1] Source: company_leave_policy.txt ...` + the question.
4. Gemini answers "Full-time employees receive 18 days of paid annual leave per calendar year [1]."
5. The app shows the answer and a **Sources** box with that chunk.

Question: *"Who is the prime minister of Canada?"* -> the closest chunks are about leave
policy, Gemini replies `INSUFFICIENT_CONTEXT`, and the app says it could not find enough information.

## Why chunk size matters
- Too small: a chunk may lack enough context to answer.
- Too big: chunks mix topics, retrieval gets blurry, and prompts cost more.
- 1000 characters / 150 overlap is a sensible starting point.

## What RAG cannot fix
- Bad text extraction (scanned PDFs, messy tables)
- Questions needing the whole document ("summarise everything") because only K chunks are retrieved
- A model that ignores instructions - the prompt reduces this but cannot guarantee it
