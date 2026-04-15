# Credit Risk System

Credit risk platform with FastAPI backend, frontend dashboard, and AI chat integrated with Gemini + Power BI context.

## What This Project Does

- AI chat for risk analysis (session-based, EN/VI support, file/context aware)
- Loan/customer/portfolio/risk management APIs
- Power BI integration for dataset schema preview and AI context enrichment
- Role-based access control (viewer/analyst/manager/admin)

## Tech Stack

- Backend: FastAPI, SQLAlchemy, MySQL, Pydantic
- AI: Google Gemini (`google-genai`)
- Frontend: Next.js
- Integrations: Power BI REST API

## Project Structure

```text
app/                 # Backend source (API routers, services, models)
apps/frontend/       # Frontend app
apps/backend/.env    # Local backend environment config
docs/                # Guides and reference docs
scripts/             # Utility and migration scripts
```

## Quick Start (Backend)

1) Create virtual env and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Configure environment file  
Edit `apps/backend/.env` (or export env vars) with at least:

```env
DATABASE_URL=mysql+pymysql://<user>:<pass>@localhost:3306/creditriskdb?charset=utf8mb4
SECRET_KEY=<your-secret>
GEMINI_API_KEY=<your-gemini-key>
AI_CHAT_PROVIDER=gemini
AI_CHAT_CONTEXT_SOURCE=powerbi
```

3) Run API

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4) Open docs

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Key API Groups

- `/api/v1/auth` - authentication
- `/api/v1/ai-chat` - AI chat sessions/messages/models
- `/api/v1/powerbi` - Power BI config/schema/query helpers
- `/api/v1/customer`, `/api/v1/loan`, `/api/v1/portfolio` - domain endpoints

## Power BI Notes

- User Power BI workspace/dataset config is stored per account.
- AI context can prioritize table hints saved from UI (`/powerbi/table-hints`).
- Schema preview endpoint: `/api/v1/powerbi/schema`.

## Important

- Do not commit secrets from `.env`.
- Some generated folders/files (`.next`, `node_modules`, `__pycache__`) should stay ignored.

## License

Proprietary/internal use.
