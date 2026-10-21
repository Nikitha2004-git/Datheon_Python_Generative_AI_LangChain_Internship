# Structured LLM Prompt Pipeline & JSON Extractor

## 1. Project overview
**AI Document Extractor** is a Streamlit app that reads the text of an **invoice** or a **resume**, asks Google Gemini to pull out specific fields, checks the answer with **Pydantic**, and shows clean, downloadable JSON.

## 2. Problem statement
Invoices and resumes are written in many styles. Copying fields by hand is slow, and AI answers can be wrong or badly formatted. This project shows how to get *predictable, validated* JSON from free-form text.

## 3. Project objectives
Practise Python, LLM integration, prompt engineering (templates + few-shot examples), JSON parsing, Pydantic validation, error handling, testing, and secure API-key handling.

## 4. Features
- Invoice and resume extraction, selectable in the interface
- Paste text, upload a `.txt` file, or load a sample
- Reusable prompt templates with few-shot examples
- Strict Pydantic validation (dates, numbers, emails, nested lists)
- Success is shown **only** after parsing and validation both pass
- Formatted JSON viewer and JSON download
- Clear errors for empty input, missing/invalid API key, rate limits, quota, timeouts, network failures, bad JSON, and schema failures
- 68 automated tests that need no API key or internet

## 5. Technologies used
| Technology | Purpose |
|---|---|
| Python 3.11+ | Language |
| Streamlit | Web interface |
| `google-genai` (official Google Gen AI SDK) | Gemini access |
| Pydantic + email-validator | Validation |
| python-dotenv | Loads `.env` |
| pytest | Tests |

## 6. Project folder structure
```
structured-llm-json-extractor/
├── app/
│   ├── main.py             # entry point
│   ├── config.py           # settings from .env
│   ├── errors.py           # custom exceptions
│   ├── llm_client.py       # Gemini communication (only AI-specific file)
│   ├── prompt_templates.py # templates + few-shot examples + document specs
│   ├── extractor.py        # extraction workflow
│   ├── schemas.py          # Pydantic models
│   ├── validators.py       # JSON parsing, validation, file decoding
│   └── ui.py               # Streamlit interface
├── examples/               # sample inputs + expected outputs
├── outputs/                # (empty) place to keep your own saved JSON
├── docs/                   # LEARNING_GUIDE.md, ARCHITECTURE.md
├── tests/
├── .streamlit/config.toml  # navy/light-blue theme
├── .env.example  .gitignore  requirements.txt  run.py
```
(`errors.py` and `.streamlit/config.toml` were added to the suggested structure to keep exceptions and theme settings tidy.)

## 7. System architecture
`User input → Streamlit UI → Prompt template → Gemini API → JSON parsing → Pydantic validation → Results + JSON download`. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 8. Prerequisites
- Windows with **Python 3.11 or later** (`python --version`)
- VS Code (optional) and Command Prompt
- A free Gemini API key

## 9–11. Installation, virtual environment, dependencies
Open Command Prompt in the project folder (in VS Code: *Terminal → New Terminal*, choose Command Prompt):
```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```
PowerShell users activate with `.venv\Scripts\Activate.ps1`.

## 12. Gemini API key setup
1. Go to <https://aistudio.google.com/apikey> and sign in.
2. Click **Create API key** and copy it.
3. Keep it private. Never paste it into code, chat, or GitHub.

## 13. Environment configuration
```bat
copy .env.example .env
```
Open `.env` and replace `your_api_key_here` with your key:
```
GEMINI_API_KEY=AIza...your key...
```
Optional settings: `GEMINI_MODEL` (default `gemini-3.5-flash-lite`; change it if Google retires that name), `REQUEST_TIMEOUT_SECONDS`, `MAX_INPUT_CHARS`, `MAX_FILE_BYTES`. `.env` is git-ignored.

## 14. How to start the application
```bat
python -m streamlit run app/main.py
```
or `python run.py`. Your browser opens at <http://localhost:8501>. Restart after editing `.env`.

## 15. How to use invoice extraction
1. Keep **Invoice Extraction** selected.
2. Click **Load sample invoice** (or paste/upload your own).
3. Click **Extract Information**.
4. Review the fields, the JSON, and the green success message.

Fields: `vendor_name`, `invoice_number`, `invoice_date` (YYYY-MM-DD), `total_amount`, `currency` (3-letter code), `customer_name`, `tax_amount`. A missing value is `null`; a real zero is `0.0`.

## 16. How to use resume extraction
Select **Resume Extraction**, load the sample resume (or your own text), click **Extract Information**. Fields: `full_name`, `email`, `phone`, `skills` (list), `education` (list of objects), `experience` (list of objects).

## 17. How to upload or paste document text
Paste into the **Document text** box, or use **Upload a .txt file** (UTF-8, up to 200 KB by default). Wrong formats, empty files, and non-text files get an error message. **Clear input** resets everything. PDF/Word files are not supported; copy their text instead.

## 18. How to download the JSON output
On the results screen click **Download JSON**. The file is named `invoice_extraction.json` or `resume_extraction.json`. Use **Back to input (edit text)** to change the text and retry. Only validated output can be downloaded.

## 19. Example input and output
Input: `examples/sample_invoice.txt`. Expected output (a real AI answer may differ slightly):
```json
{
  "vendor_name": "Northwind Office Supplies Pvt. Ltd.",
  "invoice_number": "NW-2024-0457",
  "invoice_date": "2024-04-12",
  "total_amount": 9145.0,
  "currency": "INR",
  "customer_name": "Sunrise Learning Centre",
  "tax_amount": 1395.0
}
```
See `examples/expected_resume_output.json` for the resume example.

## 20. How to run tests
```bat
python -m pytest -q
```
No API key or internet is needed; the AI is mocked.

## 21. Common errors and solutions
| Message | Fix |
|---|---|
| "Gemini API key is missing…" | Create `.env` from `.env.example`, add your key, restart |
| "The Gemini API key was rejected" | Create a new key and update `.env` |
| "rate limit reached" | Wait a minute, retry |
| "quota is exhausted" | Wait for reset or check your plan in AI Studio |
| "model was not found" | Change `GEMINI_MODEL` in `.env` |
| "could not be validated" | The AI output broke the schema; expand *Validation details*, edit the text, retry |
| `streamlit` not recognised | Activate `.venv`, use `python -m streamlit ...` |

## 22. Security considerations
- The key lives only in `.env` / environment variables; it is never displayed or logged.
- Document text is wrapped in `<document>` tags and treated as untrusted data; the prompt tells the model to ignore instructions inside it. This **reduces** prompt-injection risk but cannot fully remove it. Pydantic still blocks malformed output.
- Uploads: `.txt` only, size-limited, decoded as text, never executed.
- Logs record document type and length, not document content.
- Document text is sent to Google's API; do not use confidential documents unless that is acceptable for you.

## 23. Limitations
- **Pydantic checks structure and types, not truth.** A well-formed answer can still contain a wrong fact; always review important results.
- Live Gemini calls were **not** tested by the author of this package (no API key was available); behaviour with the real API is covered only by mocks and error-mapping tests.
- The default model name may change over time.
- Text only (no PDF/image OCR), one document at a time, no database.

## 24. Future improvements
More document types, PDF input, a second AI provider, batch processing, confidence/evidence fields, retry with error feedback.
