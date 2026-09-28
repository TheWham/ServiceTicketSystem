@echo off
REM 一次性初始化数据库(需 MySQL 已启动):建库(it_ticket_system)+ 全量表结构 + 种子数据
REM 结构与远程库/PRD-Ultimate 保持一致;00-schema.sql 由 mysqldump --no-data 导出
REM 默认 root 密码 root123(本地免安装版),远程库请自行修改 -h/-p
set MYSQL=C:\Users\Admin\.wpscomate\tools\mysql-8.0.28-winx64\bin\mysql.exe
set MYSQL_ARGS=-uroot -proot123 --default-character-set=utf8mb4
set DB=it_ticket_system
set BASE=%~dp0..\db\init

"%MYSQL%" %MYSQL_ARGS% -e "CREATE DATABASE IF NOT EXISTS %DB% DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci" || goto :eof
"%MYSQL%" %MYSQL_ARGS% %DB% < "%BASE%\00-schema.sql" || goto :eof
"%MYSQL%" %MYSQL_ARGS% %DB% < "%BASE%\10-seed.sql"
echo DB init done: %DB%
