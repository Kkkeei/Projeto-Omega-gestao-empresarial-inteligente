@echo off
setlocal
set "TASK=OMEGA A3 Bridge"
schtasks.exe /End /TN "%TASK%" >nul 2>&1
schtasks.exe /Delete /TN "%TASK%" /F >nul 2>&1
if exist "%LOCALAPPDATA%\OMEGA\A3Bridge" rmdir /S /Q "%LOCALAPPDATA%\OMEGA\A3Bridge"
echo OMEGA A3 Bridge removido.
pause
endlocal
