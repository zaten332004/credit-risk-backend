# Run backend from apps/backend
$backendPath = $PSScriptRoot
Set-Location $backendPath

$pythonFromRepoVenv = Join-Path $backendPath "../../.venv/Scripts/python.exe"
$pythonFromLocalVenv = Join-Path $backendPath ".venv/Scripts/python.exe"

if (Test-Path $pythonFromRepoVenv) {
    & $pythonFromRepoVenv -m uvicorn app.main:app --reload
} elseif (Test-Path $pythonFromLocalVenv) {
    & $pythonFromLocalVenv -m uvicorn app.main:app --reload
} else {
    python -m uvicorn app.main:app --reload
}
