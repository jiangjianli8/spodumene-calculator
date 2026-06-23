@echo off
chcp 65001 >nul
echo ========================================
echo   锂辉石计价器 - 定时行情更新设置
echo   交易时段每5分钟自动更新 + 推送GitHub
echo ========================================
echo.

REM 删除旧任务（如果存在）
schtasks /delete /tn "spodumene_price_update" /f >nul 2>&1

REM 创建新任务：每个交易日9:00触发，每5分钟重复，持续6小时15分钟（覆盖9:00-15:15）
schtasks /create /tn "spodumene_price_update" /tr "D:\ZCode-Workspace\spodumene-calculator\run_update.bat" /sc weekly /days MON,TUE,WED,THU,FRI /st 09:00 /ri 5 /du 06:15 /f

echo.
if %errorlevel% equ 0 (
    echo ✅ 定时任务创建成功！
    echo.
    echo    任务名: spodumene_price_update
    echo    执行周期: 每个交易日 9:00-15:15
    echo    刷新间隔: 每 5 分钟
    echo    流  程: 获取行情 → 更新price.json → 推送GitHub
    echo.
    echo    客户打开网页即可看到最新价格
    echo    点刷新按钮获取5分钟内最新行情
    echo    计算时价格稳定，不会跳动
) else (
    echo ❌ 创建失败，请以管理员身份运行此脚本
    echo    右键 → 以管理员身份运行
)
echo.
pause
