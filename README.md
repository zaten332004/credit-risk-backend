# CreditRisk System Monorepo

This repository is organized as a monorepo.

## Structure

```text
credit-risk-backend/
  apps/
    backend/    # Existing FastAPI backend
    frontend/   # Frontend app (placeholder)
```

## Backend

Location: `apps/backend`

Run backend in development mode from repository root:

```powershell
.\run_dev.ps1
```

Or run manually:

```powershell
Set-Location .\apps\backend
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\apps\backend\requirements.txt
```

## Frontend

Location: `apps/frontend`

You can add your frontend project here (React/Next/Vue, etc.).
