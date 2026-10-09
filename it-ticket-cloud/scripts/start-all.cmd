@echo off
REM 一键启动后端依赖:Redis + MySQL + Nacos + 三个微服务
REM 数据已持久化,无需再跑 init-db;前端单独在 frontend 目录 npm run dev
cd /d %~dp0..

echo [1/4] starting Redis (6379) ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-redis.ps1"
if errorlevel 1 exit /b 1

echo [2/4] starting MySQL (3306) ...
start "it-ticket-mysql" cmd /c "scripts\start-mysql-local.cmd"

echo [3/4] starting Nacos (8848/9848) ...
start "it-ticket-nacos" cmd /c "scripts\start-nacos.cmd"

echo waiting for Nacos to be ready (25s) ...
timeout /t 25 /nobreak >nul

echo [4/4] starting microservices ...
start "it-ticket-gateway"   cmd /c "java -jar gateway\target\it-ticket-gateway-1.0.0.jar"
start "it-ticket-user"      cmd /c "java -jar user-service\target\it-ticket-user-service-1.0.0.jar"
start "it-ticket-ticket"    cmd /c "java -jar ticket-service\target\it-ticket-ticket-service-1.0.0.jar"

echo.
echo All started. Verify: curl http://127.0.0.1:8080/api/health
echo Frontend: cd frontend ^&^& npm run dev
