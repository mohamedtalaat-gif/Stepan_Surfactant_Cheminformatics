@echo off
cd /d "%~dp0"
if not exist "%~dp0windows\start.ps1" (
  echo The files of the lab are not all here. If you opened this from inside the ZIP file,
  echo extract the ZIP first ^(right-click, Extract All^), then start this file from the new folder.
  pause
  exit /b 1
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\start.ps1"
if errorlevel 1 (
  echo.
  echo The lab could not be started. The message above says why.
  pause
)
