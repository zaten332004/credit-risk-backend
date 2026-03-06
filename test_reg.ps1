#!/usr/bin/env pwsh
# Quick registration test

$BASE = "http://localhost:8000/api/v1"

Write-Host "1️⃣  REGISTERING ANALYST..." -ForegroundColor Cyan

$body = @{
    username = "testanalyst2"
    email = "testanalyst2@gmail.com"
    password = "password123"
    full_name = "Test Analyst 2"
    registration_type = "analyst"
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "$BASE/auth/register/signup" -Method POST -Body $body -ContentType "application/json"
$data = $response.Content | ConvertFrom-Json

Write-Host "Status: $($response.StatusCode)"
Write-Host "`n📧 Email: $($data.email)" -ForegroundColor Green
Write-Host "🔐 Verification Token: $($data.verification_token)" -ForegroundColor Green
Write-Host "🔗 Verification Link: $($data.verification_link)" -ForegroundColor Blue
Write-Host "`n📝 Message:" -ForegroundColor Yellow
Write-Host "$($data.message)" -ForegroundColor White

if ($data.verification_token) {
    Write-Host "`n2️⃣  VERIFYING EMAIL..." -ForegroundColor Cyan
    $token = $data.verification_token
    
    $response = Invoke-WebRequest -Uri "$BASE/auth/register/verify-email?token=$token" -Method GET
    $verify_data = $response.Content | ConvertFrom-Json
    
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Response: $($verify_data.message)" -ForegroundColor Green
}
