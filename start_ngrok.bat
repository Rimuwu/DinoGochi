@echo off
title Ngrok DinoGochi Tunnel Runner
cd /d "%~dp0"
python tools\start_ngrok.py
pause
