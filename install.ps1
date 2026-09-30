# gea bootstrap installer — Windows.
#
#   gh api -H "Accept: application/vnd.github.raw" `
#     repos/codegeaec/gea-manager/contents/install.ps1 | iex
#
# The repository is private, so this needs the GitHub CLI logged in with an
# account that has access (winget install GitHub.cli; gh auth login).
#
# gea itself only runs on Linux/macOS/WSL (it drives herdr, which doesn't
# support native Windows). This script's only job is: make sure WSL2 +
# Ubuntu exist, then hand off to install.sh inside that distro (fetched here
# with your gh session and piped in; install.sh sets up gh inside Ubuntu).

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "  [ok] $msg" -ForegroundColor Green }

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "GitHub CLI not found. Install it (winget install GitHub.cli), run 'gh auth login' and re-run this script." -ForegroundColor Yellow
    exit 1
}
gh auth status *> $null
if (-not $?) {
    Write-Host "Not logged in to GitHub. Run 'gh auth login' with an account that can see codegeaec/gea-manager and re-run this script." -ForegroundColor Yellow
    exit 1
}

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

# Fetched with the Windows gh session; tr strips the CR PowerShell adds to lines.
$installer = (gh api -H "Accept: application/vnd.github.raw" repos/codegeaec/gea-manager/contents/install.sh) -join "`n"
$installer | wsl.exe -d Ubuntu -- bash -lc "tr -d '\r' | bash"

Write-Host ""
Write-Host "Done. Open Ubuntu (wsl.exe -d Ubuntu) and run: gea" -ForegroundColor Cyan
