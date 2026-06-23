@echo off
REM 锂辉石计价器 - 行情更新 + 自动推送到GitHub
REM 供 Windows 定时任务调用，更新行情后自动部署到网页

set PYTHON=C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe
set SCRIPT=D:\ZCode-Workspace\spodumene-calculator\update_price.py
set REPO=D:\ZCode-Workspace\spodumene-calculator

REM 第一步：获取最新行情
"%PYTHON%" "%SCRIPT%"
if %errorlevel% neq 0 (
    echo 行情更新失败，跳过推送
    exit /b 1
)

REM 第二步：自动提交推送到GitHub
cd /d "%REPO%"
git add data\price.json
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo 行情无变化，跳过推送
    exit /b 0
)
git commit -m "auto: 更新碳酸锂期货行情"
git push origin master
echo 行情已推送到GitHub Pages
