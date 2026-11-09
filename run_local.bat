@echo off
rem 本地一键运行：抓三源 -> 算指数 -> 生成页面 -> 打开（M4b：扩为三源，兜底完整）
rem 行为说明：直接写 data/（权威存储）但不自动 push——要看最新就双击本文件，
rem          要上云需手动 git push 或等云端 Actions 周五自动跑。
cd /d "%~dp0"
set PY=C:/Users/zengw/anaconda3/python.exe
if not exist "%PY%" set PY=python

echo [1/5] 抓取流感周报...
"%PY%" -X utf8 src\fetch_flu_south.py
if errorlevel 1 echo [警告] 流感周报抓取失败，继续用已有数据

echo [2/5] 抓取哨点周报（多病原/排序）...
"%PY%" -X utf8 src\fetch_sentinel.py
if errorlevel 1 echo [警告] 哨点周报抓取失败，继续用已有数据

echo [3/5] 抓取 WHO FluNet（全国背景）...
"%PY%" -X utf8 src\fetch_flunet.py
if errorlevel 1 echo [警告] FluNet 抓取失败，继续用已有数据

echo [4/5] 计算指数...
"%PY%" -X utf8 src\compute_index.py

echo [5/5] 生成页面...
"%PY%" -X utf8 src\build_site.py

start "" "site\index.html"
