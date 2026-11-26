@echo off
rem G1 virtual table on Windows: double-click this file.
rem First run: creates .venv and installs the packages (a few minutes). Later runs start in seconds.
rem To import a recording first: drag its folder (bag + S3 output) onto this file.
rem Options are passed on, e.g.:  G1_Twin.bat --run data\demo_store\runs\S2_bag --parser rules
setlocal
cd /d "%~dp0"
set "MODEL=%S5_MODEL%"
if "%MODEL%"=="" set "MODEL=qwen2.5:3b"

if exist ".venv\Scripts\python.exe" goto deps
echo [G1] Creating the Python environment - first run only ...
set "PY="
py -3.11 -c "pass" >nul 2>&1 && set "PY=py -3.11"
if not defined PY py -3.12 -c "pass" >nul 2>&1 && set "PY=py -3.12"
if not defined PY python -c "pass" >nul 2>&1 && set "PY=python"
if not defined PY goto nopython
%PY% -m venv .venv || goto nopython

:deps
if exist ".venv\.deps_ok" goto ollama
echo [G1] Installing packages - first run only, a few minutes ...
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto fail
".venv\Scripts\python.exe" -m pip install -r requirements-demo.txt || goto fail
".venv\Scripts\python.exe" -c "import open3d, numpy, PIL, yaml, networkx" || goto fail
echo ok> ".venv\.deps_ok"

:ollama
where ollama >nul 2>&1
if errorlevel 1 (
  echo [G1] Ollama is not installed: S5 uses the offline rule parser.
  goto run
)
ollama list 2>nul | findstr /C:"%MODEL%" >nul
if errorlevel 1 (
  echo [G1] Downloading the S5 model %MODEL% - about 2 GB, first run only ...
  ollama pull %MODEL%
)

:run
echo [G1] Starting the virtual table. Close this window or press Ctrl+C to stop.
".venv\Scripts\python.exe" -m demo.twin %*
pause
exit /b 0

:nopython
echo [G1] Python 3.11 was not found. Install it from https://www.python.org/downloads/release/python-3119/
echo      (tick "Add python.exe to PATH"), then double-click this file again.
pause
exit /b 1

:fail
echo [G1] Installing the packages failed. Send this window's text to the team.
pause
exit /b 1
