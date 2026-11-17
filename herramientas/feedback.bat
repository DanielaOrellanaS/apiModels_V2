@echo off
setlocal enabledelayedexpansion
cd /d F:\ApiModels\apiModels_V2

set PYTHON_PATH=C:\Users\neotrading\AppData\Local\Programs\Python\Python313\python.exe
IF NOT EXIST "%PYTHON_PATH%" (
    echo ERROR: No se encontro Python en la ruta configurada.
    pause
    exit /b
)

echo ============================================================
echo   Feedback del modelo: calibracion + reconciliacion + precio
echo ============================================================
echo.

REM Busca el historial mas reciente en datos\logs automaticamente
set HISTORIAL=
for /f "delims=" %%f in ('dir /b /o-d "datos\logs\historial_NEO_MINIMAL_*.csv" 2^>nul') do (
    if not defined HISTORIAL set HISTORIAL=datos\logs\%%f
)

if not defined HISTORIAL (
    echo No se encontro ningun historial en datos\logs\
    echo Corriendo solo con calibracion ^(sin reconciliacion de ejecucion^)...
    echo.
    "%PYTHON_PATH%" feedback_completo.py
) else (
    echo Usando historial: %HISTORIAL%
    echo.
    if exist "datos\precios" (
        "%PYTHON_PATH%" feedback_completo.py --historial "%HISTORIAL%" --precio-dir datos\precios
    ) else (
        "%PYTHON_PATH%" feedback_completo.py --historial "%HISTORIAL%"
    )
)

echo.
if exist reportes\feedback.html (
    echo Listo. Abriendo el reporte...
    start "" "reportes\feedback.html"
) else (
    echo No se genero el archivo. Revisa el error de arriba.
)
echo.
echo Para incluir la seccion C (verdad del precio real), exporta precio
echo con EXPORTAR_PRECIO_SIMPLE.mq4 y copialo a datos\precios\ (nombrado
echo SIMBOLO_PRECIO_....csv) antes de correr este .bat.
pause
