@echo off
rem Kaptan-chan Haber Asistani baslatici
set PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe
if not exist "%PYW%" set PYW=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PYW%" set PYW=pythonw.exe
start "" "%PYW%" "%~dp0kaptan.py"
