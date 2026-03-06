# Run backend from monorepo root
$backendPath = Join-Path $PSScriptRoot "apps/backend"
Set-Location $backendPath

$pythonFromRootVenv = Join-Path $PSScriptRoot ".venv/Scripts/python.exe"
$pythonFromBackendVenv = Join-Path $backendPath ".venv/Scripts/python.exe"

if (Test-Path $pythonFromRootVenv) {
    & $pythonFromRootVenv -m uvicorn app.main:app --reload
} elseif (Test-Path $pythonFromBackendVenv) {
    & $pythonFromBackendVenv -m uvicorn app.main:app --reload
} else {
    python -m uvicorn app.main:app --reload
}
