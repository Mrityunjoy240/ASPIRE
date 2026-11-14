@echo off
set PYTHONPATH=.
echo Starting ASPIRE Core Platform...
python -m uvicorn app.main:app --reload --port 8000
pause
