@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT=%%~fI"
set "DATA_DIR=%ROOT%\data"

if not exist "%DATA_DIR%" (
    mkdir "%DATA_DIR%"
)

echo [INFO] Resetting JSON data files in "%DATA_DIR%"

for %%F in (
    calendar_blocks.json
    client_notes.json
    clients.json
    contracts.json
    crm_interactions.json
    drp_history.json
    expenses.json
    invoices.json
    quotes.json
    scoped_projects.json
    sdlc_templates.json
    timer_sessions.json
    workhours.json
) do (
    >"%DATA_DIR%\%%F" echo []
)

>"%DATA_DIR%\settings.json" (
    echo {
    echo   "name": "Your Name",
    echo   "business": "Freelancer",
    echo   "currency": "USD",
    echo   "currency_symbol": "$",
    echo   "default_rate": 50.0,
    echo   "working_hours_per_day": 8.0,
    echo   "late_fee_rate": 1.5
    echo }
)

echo [OK] JSON data reset complete.
echo [INFO] On next app launch, built-in SDLC templates will be auto-seeded.

endlocal
