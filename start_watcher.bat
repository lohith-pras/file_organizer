@echo off
REM Start File Organizer Watcher
cd /d "%~dp0"
start "" pythonw watcher.py --organize-first
