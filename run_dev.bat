@echo off

echo ��������

rem ����ǰ�˷���
start "ǰ�˷���" cmd /k "cd /d E:\Neuro-Simulator\ && npm run dev"

rem ������˷���
start "��˷���" cmd /k "cd /d E:\Neuro-Simulator\backend\ && .\venv\Scripts\uvicorn.exe main:app"

echo ����������