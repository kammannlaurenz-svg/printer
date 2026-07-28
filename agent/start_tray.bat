@echo off
rem Startet den Agent im Hintergrund mit Tray-Icon (fuer den Alltag).
cd /d "%~dp0"
start "" pythonw tray_agent.py
exit
