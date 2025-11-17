# Start a static server and open the login page in the default browser.
# Usage: Right-click -> Run with PowerShell, or from PowerShell run: .\start_server.ps1
# Note: This starts a background python http.server process on port 8000.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Push-Location $scriptDir

Write-Host "Starting static server in $scriptDir on http://localhost:8000/ ..."

# Start python http.server in a new process
$py = "python"
$pyArgs = "-m http.server 8000"
try {
    Start-Process -FilePath $py -ArgumentList $pyArgs -WindowStyle Hidden -ErrorAction Stop
    Start-Sleep -Seconds 1
    Write-Host "Server started. Opening browser to login page..."
    Start-Process "http://localhost:8000/login.html"
} catch {
    Write-Host "Failed to start python server. Make sure Python is installed and on PATH."
    Write-Host $_.Exception.Message
}

Pop-Location
