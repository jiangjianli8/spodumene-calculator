@echo off
REM 锂辉石计价器 - 行情自动更新任务计划入口
REM 用法: 双击执行，或通过 Windows 任务计划调用
set PYTHON=C:\Users\admin\AppData\Local\Programs\Python\Python312\python.exe
set SCRIPT=D:\ZCode-Workspace\spodumene-calculator\update_price.py
"%PYTHON%" "%SCRIPT%"
