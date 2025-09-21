@echo off
REM 自动备份脚本
REM 使用方法: backup.bat "提交信息"

echo [信息] 开始自动备份到GitHub...

REM 添加所有更改的文件
git add .

REM 提交更改
if "%1"=="" (
    git commit -m "Automatic backup %date% %time%"
) else (
    git commit -m "%1"
)

REM 推送到GitHub
git push origin main

if %errorlevel% == 0 (
    echo [成功] 代码已成功备份到GitHub
) else (
    echo [错误] 备份失败，请检查网络连接和Git配置
)

pause