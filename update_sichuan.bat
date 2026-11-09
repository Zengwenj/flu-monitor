@echo off
rem 四川流感指数月度半自动录入（M4a/D19）：抓图+看图+输入等级+写CSV+可选推送
rem 每月官方发布新一期后双击运行一次即可
cd /d "%~dp0"
set PY=C:/Users/zengw/anaconda3/python.exe
if not exist "%PY%" set PY=python

"%PY%" -X utf8 src\update_sichuan.py
pause
