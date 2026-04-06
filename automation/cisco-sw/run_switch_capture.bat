@echo off
set /p SWITCHIP=Enter switch IP or hostname: 
set /p USERNAME=Enter username: 
set TIMESTAMP=%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

plink.exe -ssh %USERNAME%@%SWITCHIP% -m commands.txt > %SWITCHIP%_%TIMESTAMP%.txt

echo.
echo Output saved to %SWITCHIP%_%TIMESTAMP%.txt
pause