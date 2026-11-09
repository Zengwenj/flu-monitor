@echo off
rem M2 本地一键运行：抓取 -> 计算指数 -> 生成页面 -> 打开
cd /d "%~dp0"
set PY=C:/Users/zengw/anaconda3/python.exe
if not exist "%PY%" set PY=python

echo [1/3] 抓取流感周报...
"%PY%" -X utf8 src\fetch_flu_south.py
if errorlevel 1 echo [警告] 抓取失败，继续用已有数据生成页面

echo [2/3] 计算指数...
"%PY%" -X utf8 src\compute_index.py

echo [3/3] 生成页面...
"%PY%" -X utf8 src\build_site.py

start "" "site\index.html"
