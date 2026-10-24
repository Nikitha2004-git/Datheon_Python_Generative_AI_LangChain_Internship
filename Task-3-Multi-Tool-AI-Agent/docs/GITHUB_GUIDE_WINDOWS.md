# Add Task 3 to your existing GitHub repository (Windows CMD)

Repo: https://github.com/Nikitha2004-git/Datheon_Python_Generative_AI_LangChain_Internship
Do NOT create a new repo. Only a new folder `Task-3-Multi-Tool-AI-Agent/` is added; Task 1 and Task 2 are not touched.

## Before you start
Make sure you tested the project and **never** copy `.env` or `.venv` (the ZIP does not contain them). If you already ran the project, do not copy the `.env` or `.venv` folders you created.

## Steps
```
cd %USERPROFILE%\Downloads
tar -xf Task-3-Multi-Tool-AI-Agent.zip -C %TEMP%
```
If you do not have the repo on your PC yet:
```
cd %USERPROFILE%\Documents
git clone https://github.com/Nikitha2004-git/Datheon_Python_Generative_AI_LangChain_Internship.git
```
Go into the repo and update it:
```
cd %USERPROFILE%\Documents\Datheon_Python_Generative_AI_LangChain_Internship
git pull
```
Copy ONLY the Task 3 folder (no .env/.venv/caches):
```
xcopy "%TEMP%\Task-3-Multi-Tool-AI-Agent" "Task-3-Multi-Tool-AI-Agent\" /E /I /Y
```
Check what Git sees. Only `Task-3-Multi-Tool-AI-Agent/` should appear:
```
git status
```
Make sure no secrets are staged (these must print nothing):
```
git ls-files --others --exclude-standard | findstr /i "\.env$ \.venv"
```
Stage ONLY the Task 3 folder (never `git add .env`):
```
git add Task-3-Multi-Tool-AI-Agent
git status
git commit -m "Add Task 3: Multi-Tool Autonomous AI Agent"
git push origin main
```
(If your branch is `master`, use `git push origin master`; check with `git branch`.)

## If something looks wrong
* Task 1/2 files listed as modified -> do not commit; run `git restore Task-1-Structured-JSON-Extractor Task-2-Document-QA-RAG`.
* You accidentally staged `.env` -> `git restore --staged Task-3-Multi-Tool-AI-Agent\.env` (and if it was ever pushed, **revoke the key** at Google AI Studio and create a new one).
* Authentication prompt on push -> sign in with GitHub in the browser window, or use a Personal Access Token as the password.
