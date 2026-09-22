@echo off
set MYSQL_HOME=C:\Users\Admin\.wpscomate\tools\mysql-8.0.28-winx64
if not exist "%MYSQL_HOME%\data\ibdata1" (
  echo Initializing data dir ...
  "%MYSQL_HOME%\bin\mysqld.exe" --initialize-insecure --basedir="%MYSQL_HOME%" --datadir="%MYSQL_HOME%\data" --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
)
echo Starting mysqld on 3306 ...
"%MYSQL_HOME%\bin\mysqld.exe" --console --basedir="%MYSQL_HOME%" --datadir="%MYSQL_HOME%\data" --port=3306 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
