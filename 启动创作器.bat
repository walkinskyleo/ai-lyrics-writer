@echo off
setlocal
rem ============================================
rem  Ai Lyrics Writer（AI歌词创作器）- GUI 启动器
rem  双击本文件即可启动可视化创作界面
rem  界面未弹出时，请查看同目录 gui_error.log
rem ============================================

cd /d "%~dp0"

set "SCRIPT=scripts\lyrics_gui.py"
set "ERRLOG=gui_error.log"

rem ---- 1. 查找 pythonw（GUI 版，无黑窗口；排除 Microsoft Store 别名）----
set "PYW="
where pythonw >nul 2>nul && set "PYW=pythonw"
if defined PYW (
  echo "%PYW%" | findstr /i "WindowsApps" >nul && set "PYW="
)
if not defined PYW (
  for /d %%D in ("C:\Python*") do if exist "%%D\pythonw.exe" set "PYW=%%D\pythonw.exe"
)
if not defined PYW (
  for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do if exist "%%D\pythonw.exe" set "PYW=%%D\pythonw.exe"
)
rem 豆包桌面客户端自带运行时（未装系统 Python 时的后备）
if not defined PYW (
  for /d %%D in ("%LOCALAPPDATA%\Doubao\User Data\sandbox_runtime\bases\*") do if exist "%%D\python\pythonw.exe" set "PYW=%%D\python\pythonw.exe"
)

rem ---- 2. 检查 tkinter；缺失则放弃 pythonw ----
set "TK_MISSING="
if defined PYW (
  "%PYW%" -c "import tkinter" >nul 2>nul
  if errorlevel 1 (
    set "TK_MISSING=1"
    set "PYW="
  )
)

rem ---- 3. 兜底查找 python（带控制台窗口）----
set "PY="
if not defined PYW (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    echo %%P | findstr /i "WindowsApps" >nul || set "PY=%%P"
  )
)
if not defined PY (
  for /d %%D in ("C:\Python*") do if exist "%%D\python.exe" set "PY=%%D\python.exe"
)
if not defined PY (
  for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do if exist "%%D\python.exe" set "PY=%%D\python.exe"
)
if not defined PY (
  for /d %%D in ("%LOCALAPPDATA%\Doubao\User Data\sandbox_runtime\bases\*") do if exist "%%D\python\python.exe" set "PY=%%D\python\python.exe"
)
if defined PY (
  "%PY%" -c "import tkinter" >nul 2>nul
  if errorlevel 1 set "PY="
)

rem ---- 4. 启动 ----
if defined PYW (
  start "" "%PYW%" "%SCRIPT%" 2>"%ERRLOG%"
  exit /b 0
)
if defined PY (
  start "" "%PY%" "%SCRIPT%" 2>"%ERRLOG%"
  exit /b 0
)

rem ---- 5. 全部失败：提示 ----
echo.
echo [错误] 无法启动 Ai Lyrics Writer（AI歌词创作器）。
if defined TK_MISSING (
  echo 检测到 Python，但缺少 tkinter 模块（Tcl/Tk）。
  echo 请重新安装 Python 3，在安装向导中勾选 "tcl/tk and IDLE"。
) else (
  echo 未检测到 Python 3。
  echo 请安装 Python 3（python.org 下载，勾选 "Add to PATH" 与 "tcl/tk and IDLE"）。
  echo 安装完成后，重新双击本文件即可。
)
echo 若界面仍未弹出，请查看同目录下的 gui_error.log 日志。
echo.
pause
