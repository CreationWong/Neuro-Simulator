@echo off
setlocal enabledelayedexpansion

:: �Զ���ȡ�ű�����Ŀ¼��Ϊ��Ŀ��Ŀ¼
set "ROOT_DIR=%~dp0"
:: �Ƴ�·��ĩβ�ķ�б�ܣ�����У�
if "!ROOT_DIR:~-1!"=="\" set "ROOT_DIR=!ROOT_DIR:~0,-1!"

:: ����ǰ�˷���
start "ǰ�˷���" cmd /k "cd /d "!ROOT_DIR!\" && echo ǰ��Ŀ¼: !ROOT_DIR! && npm run dev"

:: ������˷���
start "��˷���" cmd /k "cd /d "!ROOT_DIR!\backend" && echo ���Ŀ¼: !ROOT_DIR!\backend && .\venv\Scripts\uvicorn.exe main:app"