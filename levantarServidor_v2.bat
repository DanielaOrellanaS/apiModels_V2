@echo off
setlocal
REM Cambiar al directorio del proyecto nuevo
cd /d F:\ApiModels\apiModels_V2

REM Verificar que Python existe (misma ruta que ya usás)
set PYTHON_PATH=C:\Users\neotrading\AppData\Local\Programs\Python\Python313\python.exe
IF NOT EXIST "%PYTHON_PATH%" (
    echo ERROR: No se encontro Python en la ruta configurada.
    pause
    exit /b
)

REM Verificar que el entorno virtual existe
IF NOT EXIST "env\Scripts\activate.bat" (
    echo El entorno virtual no existe. Creandolo...
    "%PYTHON_PATH%" -m venv env
)

REM Activar el entorno virtual
call env\Scripts\activate.bat
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR al activar el entorno virtual.
    pause
    exit /b
)

REM Instalar dependencias dentro del entorno virtual (solo la primera vez
REM hace algo -- despues es instantaneo, pip se fija que ya estan)
pip install pandas numpy scikit-learn joblib fastapi uvicorn >nul 2>&1

echo Entorno virtual activado.
echo Iniciando servidor NUEVO (ApiModels_v2) en 127.0.0.1 puerto 80 (localhost, no choca con la vieja que esta en 172.16.0.4)...
REM Puerto DISTINTO al de la API vieja (80) -- las dos quedan corriendo
REM en paralelo. GER40 sigue usando la vieja sin tocarla.
REM SIN --reload: eso vigila la carpeta entera y reinicia el servidor solo
REM ante cualquier cambio de archivo (un modelo nuevo, un reporte, registry.json).
REM Sirve para cuando se esta editando codigo, pero deja el servidor inestable
REM para dejarlo corriendo en demo/real -- puede colgar un pedido a mitad de camino.
"%PYTHON_PATH%" -m uvicorn api:app --host 127.0.0.1 --port 80

IF %ERRORLEVEL% EQU 0 (
    echo Servidor iniciado correctamente.
) ELSE (
    echo ERROR al iniciar el servidor. Codigo de salida: %ERRORLEVEL%
)
pause
