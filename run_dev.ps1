# Development server runner
Write-Host "🚀 Starting Credit Risk Backend Development Server..." -ForegroundColor Green
Write-Host ""

# Navigate to project directory
Set-Location "d:\GitHub\credit-risk-backend"

# Activate venv and run server
if (-not $env:GEMINI_API_KEY -and -not $env:AI_CHAT_PROVIDER) {
    $env:AI_CHAT_PROVIDER = "mock"
    Write-Host "ℹ️  GEMINI_API_KEY missing → AI_CHAT_PROVIDER=mock (for local testing)" -ForegroundColor Yellow
}
& ".venv/Scripts/python.exe" -m uvicorn app.main:app --reload

Write-Host ""
Write-Host "✅ Server stopped" -ForegroundColor Green
