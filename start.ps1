# Offline-ready Round 2 demo launch. Install dependencies before arriving.
$ErrorActionPreference = 'Stop'
$backendDir = Join-Path $PSScriptRoot 'backend'
$frontendDir = Join-Path $PSScriptRoot 'frontend'
$venvPython = Join-Path $backendDir '.venv\Scripts\python.exe'
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonExe) {
        throw 'Python is missing. Install backend requirements before the demo.'
    }
}
if (-not (Test-Path (Join-Path $frontendDir 'node_modules'))) {
    throw 'Frontend dependencies are missing. Run npm ci in frontend before the demo.'
}
$npmExe = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
if (-not $npmExe) {
    throw 'npm is missing. Install Node.js before the demo.'
}
$api = Start-Process -FilePath $pythonExe -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru
$ui = Start-Process -FilePath $npmExe -ArgumentList 'run','dev','--','--host','127.0.0.1' -WorkingDirectory $frontendDir -WindowStyle Hidden -PassThru
Write-Host "API PID $($api.Id), UI PID $($ui.Id). Open http://127.0.0.1:5173/"
Write-Host 'To stop them: Stop-Process -Id <API PID>,<UI PID>'
