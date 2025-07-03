@echo off
setlocal enabledelayedexpansion

:: 自动获取脚本所在目录作为项目根目录
set "ROOT_DIR=%~dp0"
:: 移除路径末尾的反斜杠（如果有）
if "!ROOT_DIR:~-1!"=="\" set "ROOT_DIR=!ROOT_DIR:~0,-1!"

:: 启动前端服务
start "前端服务" cmd /k "cd /d "!ROOT_DIR!\" && echo 前端目录: !ROOT_DIR! && npm run dev"

:: 启动后端服务
start "后端服务" cmd /k "cd /d "!ROOT_DIR!\backend" && echo 后端目录: !ROOT_DIR!\backend && .\venv\Scripts\uvicorn.exe main:app"