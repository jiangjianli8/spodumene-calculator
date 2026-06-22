@echo off
chcp 65001 >nul
echo ========================================
echo   锂辉石计价器 - 定时行情更新设置
echo ========================================
echo.
echo 正在创建 Windows 定时任务...
schtasks /create /tn "spodumene_price_update" /tr "D:\ZCode-Workspace\spodumene-calculator\run_update.bat" /sc weekly /days MON,TUE,WED,THU,FRI /st 15:15 /f
echo.
if %errorlevel% equ 0 (
    echo ✅ 定时任务创建成功！
    echo    任务名: spodumene_price_update
    echo    执行时间: 每个交易日 15:15
    echo    说明: 收盘后自动更新碳酸锂期货行情
) else (
    echo ❌ 创建失败，请以管理员身份运行此脚本
    echo    右键 → 以管理员身份运行
)
echo.
pause
