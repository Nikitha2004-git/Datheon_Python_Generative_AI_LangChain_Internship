# Run guide for Windows (Command Prompt + VS Code)

Use **Command Prompt** (press Start, type `cmd`) or the VS Code terminal set to Command Prompt.

## 0. Check Python
```bat
python --version
```
You need 3.10 - 3.13. If it fails, install Python from python.org and tick **Add python.exe to PATH**.

## 1. Extract the ZIP
Windows 10/11 has `tar`:
```bat
cd %USERPROFILE%\Downloads
tar -xf Task-2-Document-QA-RAG.zip
```
(Or right-click the ZIP -> Extract All.) A folder `Task-2-Document-QA-RAG` appears.
If the ZIP extracts into a folder inside a folder, use the inner one that contains `requirements.txt`.

## 2. Open the correct folder
```bat
cd Task-2-Document-QA-RAG
dir
```
You should see `app`, `tests`, `requirements.txt`, `README.md`. In VS Code: File -> Open Folder -> choose this folder.

## 3. Create and activate a virtual environment
```bat
python -m venv .venv
.venv\Scripts\activate
```
The prompt starts with `(.venv)`. If PowerShell blocks activation, use Command Prompt instead.

## 4. Install dependencies
```bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```
This takes several minutes (PyTorch is large). Needs internet.

## 5. Create `.env` and add your key
Get a free key: https://aistudio.google.com/apikey
```bat
copy .env.example .env
notepad .env
```
Change the line to `GEMINI_API_KEY=` followed by your key, with no quotes or spaces. Save and close.
Never share this file and never commit it. Check setup (does not print the key):
```bat
python run.py --check
```

## 6. Run the app
```bat
python -m streamlit run app/main.py
```
Open http://localhost:8501 if the browser does not open. Stop with `Ctrl+C`.
The first **Process documents** click downloads the embedding model (~90 MB).

## 7. Run the tests
```bat
python -m pytest
```

## 8. Clean up stored data
```bat
python run.py --clean
```

---

## Adding Task 2 to GitHub

Goal: add the folder next to Task 1 in the **same** repository without touching Task 1.

### A. Look before you change anything
```bat
cd path\to\Datheon_Python_Generative_AI_LangChain_Internship
git status
git branch
git log --oneline -5
dir
```
- `git status` should say "working tree clean". If it lists changes, commit or stash them first.
- `dir` shows your structure. If you already have `Task-1-Structured-JSON-Extractor`, you are ready for step B.

### If Task 1 files are directly in the repo root (no Task 1 folder)
Moving files with `git mv` keeps their history. Do this as its own commit, and **read each command first**:
```bat
mkdir Task-1-Structured-JSON-Extractor
git mv app.py Task-1-Structured-JSON-Extractor\
```
Repeat `git mv` for each Task 1 file or folder (use `git status` to list them). Do **not** move `.git`, and leave `.gitignore` in the root if it covers several tasks. Then:
```bat
git status
git commit -m "Move Task 1 into its own folder"
```
Run Task 1 once afterwards to confirm paths such as `.env` or data folders still work (you may need to
copy your local `.env` into the new folder; `.env` is not tracked by Git).

### B. Copy Task 2 in
Copy the extracted `Task-2-Document-QA-RAG` folder into the repository root using File Explorer. Make sure you do **not** copy `.venv`, `chroma_db`, or your real `.env`.

### C. Check, stage only Task 2, commit, push
```bat
git status
```
Confirm the only new path is `Task-2-Document-QA-RAG/` and **`.env` is not listed**. Then:
```bat
git add Task-2-Document-QA-RAG
git status
git commit -m "Add Task 2: Document Q&A Assistant (RAG)"
git push
```
If `git push` is rejected because GitHub has newer commits, run `git pull --rebase` or `git pull`, resolve anything Git reports, then push again.
Never use `git push --force` or `git reset --hard`.

### D. Verify
Open the repository on GitHub and confirm Task 1 and Task 2 folders both exist and no `.env` file is visible.
If a secret was ever pushed, **revoke the key** in Google AI Studio and create a new one.

### E. Repository name
Requested name `Datheon_Python_+_Generative_AI_&_LangChain_Internship` contains `+` and `&`, which GitHub does not allow.
Use `Datheon_Python_Generative_AI_LangChain_Internship`.
