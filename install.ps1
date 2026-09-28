# gea bootstrap installer — Windows.
#
#   irm https://raw.githubusercontent.com/codegeaec/gea-manager/main/install.ps1 | iex
#
# gea itself only runs on Linux/macOS/WSL (it drives herdr, which doesn't
# support native Windows). This script's only job is: make sure WSL2 +
# Ubuntu exist, then hand off to install.sh inside that distro.

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [ok] $msg" -ForegroundColor Green }

$wslInstalled = (wsl.exe --status) 2>$null
if (-not $?) {
    Write-Info "WSL not found — installing WSL2 with Ubuntu (this needs a restart)"
    wsl.exe --install -d Ubuntu
    Write-Host ""
    Write-Host "Restart your machine, then re-run this script to continue." -ForegroundColor Yellow
    exit 0
}

$distros = (wsl.exe -l -q) 2>$null | ForEach-Object { $_.Trim() }
if (-not ($distros -contains "Ubuntu")) {
    Write-Info "Installing Ubuntu on WSL2"
    wsl.exe --install -d Ubuntu
    Write-Host ""
    Write-Host "Finish the Ubuntu first-run setup (username/password), then re-run this script." -ForegroundColor Yellow
    exit 0
}

Write-Ok "WSL2 + Ubuntu present"
Write-Info "Running gea's installer inside Ubuntu"

$installCmd = "curl -fsSL https://raw.githubusercontent.com/codegeaec/gea-manager/main/install.sh | bash"
wsl.exe -d Ubuntu -- bash -lc $installCmd

Write-Host ""
Write-Host "Done. Open Ubuntu (wsl.exe -d Ubuntu) and run: gea" -ForegroundColor Cyan
