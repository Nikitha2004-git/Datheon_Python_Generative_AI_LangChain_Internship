# Run Guide - Windows Command Prompt (CMD)

Open **Command Prompt** (Win + R, type `cmd`, Enter). Needs Python 3.11 or 3.12 (`py -3.12 --version`).

## 1. Extract the ZIP
Put `Task-3-Multi-Tool-AI-Agent.zip` in your Downloads folder, then:
```
cd %USERPROFILE%\Downloads
tar -xf Task-3-Multi-Tool-AI-Agent.zip
cd Task-3-Multi-Tool-AI-Agent
```
(If the ZIP extracts into a nested folder, `cd` into the one containing `run.py`.)

## 2. Virtual environment and install
```
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```
You should see `(.venv)` at the start of the prompt.

## 3. Configure the API key
```
copy .env.example .env
notepad .env
```
Replace `your_api_key_here` with your key from https://aistudio.google.com/apikey, save, close. Do not use quotes. Never share or commit `.env`.

## 4. Check configuration (no secrets shown)
```
python run.py --check
```

## 5. Run tests (no key/internet needed)
```
python -m pytest
```

## 6. Run the agent
```
python run.py
```
Type `exit` to quit. One-shot mode:
```
python run.py -q "Calculate (1250 * 3) + 450."
```

## 7. Demo questions
```
python run.py -q "Calculate (1250 * 3) + 450."
python run.py -q "Read the company information from the permitted sample file."
python run.py -q "Search for the latest Python release and summarize the sources."
python run.py -q "Read the project budget file, calculate the remaining budget, and explain the result."
python run.py -q "Who is the CEO of Northwind Demo Traders and what is their phone number?"
python run.py -q "Read the file .env"
```
Expected: 4200; file contents; sources with URLs from the search; remaining budget 140000; a statement that the info is not available; access denied.

## 8. Leave the virtual environment
```
deactivate
```
