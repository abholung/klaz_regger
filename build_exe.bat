@echo off
setlocal

python -m venv .venv
call .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
python -m playwright install

pyinstaller --noconsole --onefile -n regger_gui -m regger.gui

echo.
echo Build complete. EXE is at dist\regger_gui.exe
pause
