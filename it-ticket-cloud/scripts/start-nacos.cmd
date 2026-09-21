@echo off
REM 本地开发:以 standalone 模式启动 Nacos(假设已解压到 %NACOS_HOME%)
REM 用法:scripts\start-nacos.cmd [Nacos安装目录]
set NACOS_DIR=%1
if "%NACOS_DIR%"=="" set NACOS_DIR=C:\Users\Admin\.wpscomate\tools\nacos
echo Starting Nacos (standalone) at %NACOS_DIR% ...
call "%NACOS_DIR%\bin\startup.cmd" -m standalone
