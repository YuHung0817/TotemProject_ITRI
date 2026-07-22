$ErrorActionPreference = "Stop"
Push-Location backend
try { & ..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000 } finally { Pop-Location }

