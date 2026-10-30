# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
#
# Starts the Stepan Surfactant Cheminformatics dry lab on Windows. The first start downloads a Python runtime and
# the packages pinned in uv.lock into this folder; later starts take seconds.

$ErrorActionPreference = "Stop"
# Older Windows PowerShell does not offer TLS 1.2 by default, which the downloads below need.
try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { }
# Python then reads and writes text as UTF-8 whatever the Windows language settings are.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$pidFile = Join-Path $root ".lab.pid"
$portFile = Join-Path $root ".lab.port"
$logFile = Join-Path $root ".lab.log"
$errFile = Join-Path $root ".lab.err.log"
$tools = Join-Path $root ".tools"

function Open-Page($address) {
    if (-not $env:LAB_NO_BROWSER) { Start-Process $address }
}

Write-Host "Stepan Surfactant Cheminformatics"
Write-Host "Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University"
Write-Host ""

# Already running: open the page again.
if ((Test-Path $pidFile) -and (Test-Path $portFile)) {
    $oldPid = (Get-Content $pidFile -TotalCount 1)
    if ($oldPid -match "^\d+$" -and (Get-Process -Id ([int]$oldPid) -ErrorAction SilentlyContinue)) {
        $address = "http://127.0.0.1:" + (Get-Content $portFile -TotalCount 1) + "/"
        Write-Host "The lab is already running at $address"
        Open-Page $address
        exit 0
    }
}
Remove-Item $pidFile, $portFile -Force -ErrorAction SilentlyContinue

# Step 1: uv, the tool that installs Python and the packages.
$uv = Join-Path $tools "uv.exe"
if (-not (Test-Path $uv)) {
    $found = Get-Command uv -ErrorAction SilentlyContinue
    if ($found) {
        $uv = $found.Source
    } else {
        Write-Host "Step 1 of 3: downloading uv, the tool that installs Python and the packages (about 20 MB)"
        New-Item -ItemType Directory -Force $tools | Out-Null
        $env:UV_UNMANAGED_INSTALL = $tools
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        if (-not (Test-Path $uv)) {
            throw "uv could not be downloaded. Check the internet connection and start again."
        }
    }
}

# Step 2: Python 3.12 and the packages, kept inside this folder.
$env:UV_PYTHON_INSTALL_DIR = Join-Path $tools "python"
$env:UV_CACHE_DIR = Join-Path $tools "cache"
Write-Host "Step 2 of 3: installing Python and the packages (first start only, a few minutes)"
& $uv sync --frozen
if ($LASTEXITCODE -ne 0) {
    throw "The packages could not be installed. Check the internet connection and start again."
}
$python = Join-Path $root ".venv\Scripts\python.exe"

# Step 3: start the server on a free port.
$port = 2718
while ((Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) -and $port -lt 2740) { $port++ }
Write-Host "Step 3 of 3: starting the lab"
$arguments = "-m uvicorn server:app --host 127.0.0.1 --port $port"
$process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput $logFile -RedirectStandardError $errFile -PassThru
$process.Id | Set-Content -Path $pidFile -Encoding ascii
$port | Set-Content -Path $portFile -Encoding ascii
$address = "http://127.0.0.1:$port/"

for ($attempt = 0; $attempt -lt 120; $attempt++) {
    Start-Sleep -Milliseconds 500
    if ($process.HasExited) { throw "The server stopped while starting. The log is in $errFile" }
    try {
        Invoke-WebRequest -Uri $address -UseBasicParsing -TimeoutSec 2 | Out-Null
        Write-Host ""
        Write-Host "The lab is running at $address and opens in your browser."
        Write-Host "To stop it, use the Stop file in this folder."
        Open-Page $address
        exit 0
    } catch { }
}
throw "The server did not answer within a minute. The log is in $errFile"
