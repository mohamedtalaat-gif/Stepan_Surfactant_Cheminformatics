# Created by Muhammad Talaat, Faculty of Pharmacy, Ain Shams University
# SPDX-FileCopyrightText: 2026 Muhammad Talaat
# SPDX-License-Identifier: MIT
#
# Stops the Stepan Surfactant Chemistry: a Cheminformatics Dry Lab lab that windows/start.ps1 started.

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pidFile = Join-Path $root ".lab.pid"
$stopped = $false
if (Test-Path $pidFile) {
    $labPid = Get-Content -Path $pidFile -TotalCount 1
    if ($labPid -match "^\d+$" -and (Get-Process -Id ([int]$labPid))) {
        # the python.exe of a virtual environment starts the real interpreter as a child: stop the whole tree
        & taskkill.exe /PID $labPid /T /F | Out-Null
        if (Get-Process -Id ([int]$labPid)) { Stop-Process -Id ([int]$labPid) -Force }
        $stopped = $true
    }
}
Remove-Item $pidFile, (Join-Path $root ".lab.port") -Force
if ($stopped) { Write-Host "The lab has been stopped." } else { Write-Host "No running lab was found." }
