@echo off
REM 一次性初始化数据库:建库(it_ticket_system)+ 全量表结构 + 种子数据
REM 结构与 PRD-Ultimate 保持一致;00-schema.sql 由 mysqldump --no-data 导出
REM 数据库统一连远程库 120.92.138.195:3306(默认密码 clt123456)
REM 可用环境变量覆盖:MYSQL_HOST / MYSQL_PORT / MYSQL_USERNAME / MYSQL_PASSWORD
set MYSQL=C:\Users\Admin\.wpscomate\tools\mysql-8.0.28-winx64\bin\mysql.exe
if "%MYSQL_HOST%"=="" set MYSQL_HOST=120.92.138.195
if "%MYSQL_PORT%"=="" set MYSQL_PORT=3306
if "%MYSQL_USERNAME%"=="" set MYSQL_USERNAME=root
if "%MYSQL_PASSWORD%"=="" set MYSQL_PASSWORD=clt123456
set MYSQL_ARGS=-h%MYSQL_HOST% -P%MYSQL_PORT% -u%MYSQL_USERNAME% -p%MYSQL_PASSWORD% --default-character-set=utf8mb4
set DB=it_ticket_system
set BASE=%~dp0..\db\init

"%MYSQL%" %MYSQL_ARGS% -e "CREATE DATABASE IF NOT EXISTS %DB% DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci" || goto :eof
"%MYSQL%" %MYSQL_ARGS% %DB% < "%BASE%\00-schema.sql" || goto :eof
"%MYSQL%" %MYSQL_ARGS% %DB% < "%BASE%\10-seed.sql"
echo DB init done: %DB%
