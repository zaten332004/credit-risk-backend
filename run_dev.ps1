# Development server runner
Write-Host "🚀 Starting Credit Risk Backend Development Server..." -ForegroundColor Green
Write-Host ""

# Navigate to project directory
Set-Location "d:\GitHub\credit-risk-backend"

# Activate venv and run server
& ".venv/Scripts/python.exe" -m uvicorn app.main:app --reload

Write-Host ""
Write-Host "✅ Server stopped" -ForegroundColor Green
