@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   易学酷批量查询 - 一键运行
echo ========================================
echo.

py -3 -c "import openpyxl, requests" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖，请稍候...
    py -3 -m pip install -r requirements.txt
)

if exist "dist\易学酷信息获取_*.exe" (
    for %%F in ("dist\易学酷信息获取_*.exe") do (
        echo 使用已打包程序: %%~nxF
        "%%~fF"
        goto :done
    )
)

py -3 yxk_batch_runner.py

:done
if errorlevel 1 (
    echo.
    echo 运行失败，请检查上方错误信息。
    pause
)
