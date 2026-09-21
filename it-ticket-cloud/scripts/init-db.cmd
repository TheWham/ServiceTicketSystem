@echo off
REM 一次性初始化数据库(需 MySQL 已启动):建库 + 建表 + 种子数据
REM 默认 root 无密码(免安装版 --initialize-insecure),密码不同请改下面的 -p
set MYSQL=C:\Users\Admin\.wpscomate\tools\mysql-8.0.28-winx64\bin\mysql.exe
set MYSQL_ARGS=-uroot -proot123 --default-character-set=utf8mb4
set BASE=%~dp0..\db\init
"%MYSQL%" %MYSQL_ARGS% < "%BASE%\00-create-databases.sql" || goto :eof
"%MYSQL%" %MYSQL_ARGS% < "%BASE%\10-user-db.sql"
"%MYSQL%" %MYSQL_ARGS% < "%BASE%\11-user-seed.sql"
"%MYSQL%" %MYSQL_ARGS% < "%BASE%\20-ticket-db.sql"
"%MYSQL%" %MYSQL_ARGS% < "%BASE%\21-ticket-seed.sql"
echo DB init done.
