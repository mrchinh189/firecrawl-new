@echo off
REM Chạy 1 lần bộ monitor (dùng cho Windows Task Scheduler khi KHÔNG dùng Docker).
REM Trong Task Scheduler: Action = Start a program, Program = đường dẫn tới file .bat này.
cd /d "%~dp0"
python monitor.py >> monitor.log 2>&1
