@echo off
setlocal
cd /d F:\ApiModels\apiModels_V2

set PYTHON_PATH=C:\Users\neotrading\AppData\Local\Programs\Python\Python313\python.exe
IF NOT EXIST "%PYTHON_PATH%" (
    echo ERROR: No se encontro Python en la ruta configurada.
    pause
    exit /b
)

echo ============================================================
echo   Reporte de winrate — NAS100, GER40, US30, BTCUSD
echo   Ventanas de 30 y 60 dias, sobre el historial mas reciente
echo   exportado desde MT4 (datos\logs\historial_NEO_MINIMAL_*.csv)
echo ============================================================
echo.

"%PYTHON_PATH%" winrate_reporte.py

echo.
echo ============================================================
echo   Si no se ve la operacion mas reciente que esperabas:
echo   1. Arrastra EXPORTAR_HISTORIAL_NEO_MINIMAL.mq4 sobre
echo      cualquier grafico en MT4 (genera un CSV nuevo)
echo   2. Copia ese CSV a datos\logs\ en esta carpeta
echo   3. Volve a correr este .bat
echo ============================================================
pause
