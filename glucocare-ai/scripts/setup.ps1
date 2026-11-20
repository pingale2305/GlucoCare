# One-time setup (Windows PowerShell). Run from the project root:
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  $bytes = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  $key = ([BitConverter]::ToString($bytes) -replace "-", "").ToLower()
  (Get-Content ".env") -replace "^SECRET_KEY=.*", "SECRET_KEY=$key" | Set-Content ".env"
  Write-Host "Created .env with a random SECRET_KEY"
}

Set-Location "$root\backend"
if (-not (Test-Path "venv")) { python -m venv venv }
& ".\venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "`n[1/3] Cleaning datasets";   & ".\venv\Scripts\python.exe" -m app.scripts.process_datasets
Write-Host "`n[2/3] Creating doctor account"; & ".\venv\Scripts\python.exe" -m app.scripts.seed
Write-Host "`n[3/3] Importing datasets into glucocare.db (1-2 min)"; & ".\venv\Scripts\python.exe" -m app.scripts.import_datasets

Set-Location "$root\frontend"
npm install
Write-Host "`nSetup complete. Start the app with scripts\run-backend.ps1 and scripts\run-frontend.ps1 (two terminals)."
