@echo off

echo 正在启动

rem 启动前端服务
start "前端服务" cmd /k "cd /d E:\Neuro-Simulator\ && npm run dev"

rem 启动后端服务
start "后端服务" cmd /k "cd /d E:\Neuro-Simulator\backend\ && .\venv\Scripts\uvicorn.exe main:app"

echo 服务已启动