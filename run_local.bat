@echo off
rem 本地一键运行：统一管线（六源抓取 -> 三个指数 -> 五页构建 -> 打开）
rem 行为说明：写 data/（权威存储）但不自动 push。管线退出 0/1 才打开本轮已校验的页面；
rem          退出 2（构建失败/另一实例在跑）不打开旧页。
cd /d "%~dp0"
set PY=C:/Users/zengw/anaconda3/python.exe
if not exist "%PY%" set PY=python

"%PY%" -X utf8 src\run_pipeline.py --local --open
set RC=%ERRORLEVEL%

if "%RC%"=="0" goto done
if "%RC%"=="1" echo [警告] 部分数据源本轮失败，页面已按诚实降级生成（详见上方日志）
if "%RC%"=="2" echo [错误] 管线或构建失败，未打开页面；请查看上方日志
:done
if not "%RC%"=="0" if not "%RC%"=="1" pause
