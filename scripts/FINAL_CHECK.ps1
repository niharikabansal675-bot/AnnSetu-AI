param([switch]$SkipLive)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backendPy = Join-Path $project 'backend\.venv\Scripts\python.exe'
$mlPy = Join-Path $project 'ml_service\.venv\Scripts\python.exe'
if (!(Test-Path $backendPy)) { throw "Backend venv missing: $backendPy" }
if (!(Test-Path $mlPy)) { throw "ML venv missing: $mlPy" }
Push-Location (Join-Path $project 'backend')
try {
 Write-Host '1/4: Backend code compilation'
 & $backendPy -m compileall -q app
 if ($LASTEXITCODE -ne 0) { throw 'Backend compile failed' }
 Write-Host '2/4: T3 bridge regression tests'
 & $backendPy -m unittest discover -s tests -p 'test_release_bridge.py' -v
 if ($LASTEXITCODE -ne 0) { throw 'Backend bridge tests failed' }
} finally { Pop-Location }
Push-Location $project
try {
 Write-Host '3/4: ML service contract tests'
 & $mlPy -m unittest discover -s ml_service/tests -p 'test_release_model.py' -v
 if ($LASTEXITCODE -ne 0) { throw 'ML contract tests failed' }
 if (!$SkipLive) {
  Write-Host '4/4: Read-only HTTP health probes (start both servers first)'
  foreach ($uri in @('http://127.0.0.1:8000/api/health', 'http://127.0.0.1:8100/health')) {
   try { $r = Invoke-RestMethod -Uri $uri -Method GET -TimeoutSec 4; Write-Host "$uri => $($r.status)" }
   catch { Write-Warning "$uri unavailable. Start server in a separate terminal: $($_.Exception.Message)" }
  }
 } else { Write-Host '4/4: Live HTTP probes skipped.' }
 Write-Host 'FINISHED. This does NOT validate PostgreSQL concurrency or deployed GPU inference.'
} finally { Pop-Location }
