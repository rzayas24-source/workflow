@echo off
title Site Module Launcher

echo ============================================
echo   Launching Site Streamlit Module
echo ============================================
echo.

REM Change directory to the folder where this BAT file lives
cd /d "%~dp0"

REM Run Streamlit with your main app
streamlit run site_app.py

echo.
echo ============================================
echo   Streamlit closed
echo ============================================
pause
