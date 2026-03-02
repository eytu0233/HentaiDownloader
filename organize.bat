@echo off
chcp 65001 >nul
echo ========================================
echo 作者分類整理工具
echo ========================================
echo.

set "DOWNLOAD_PATH=E:\video\合集\downloads"

echo 預設下載目錄: %DOWNLOAD_PATH%
echo.
echo 功能選單：
echo ┌────────────────────────────────────┐
echo │ 整理模式（單目錄整理）             │
echo ├────────────────────────────────────┤
echo │ 1. 測試運行（不實際移動文件）      │
echo │ 2. 正式執行                        │
echo │ 3. 自訂路徑測試運行                │
echo │ 4. 自訂路徑正式執行                │
echo ├────────────────────────────────────┤
echo │ 合併模式（兩目錄合併）             │
echo ├────────────────────────────────────┤
echo │ 5. 合併作者目錄（測試運行）        │
echo │ 6. 合併作者目錄（正式執行）        │
echo ├────────────────────────────────────┤
echo │ 清除模式                           │
echo ├────────────────────────────────────┤
echo │ 7. 刪除空目錄（測試運行）          │
echo │ 8. 刪除空目錄（正式執行）          │
echo ├────────────────────────────────────┤
echo │ 9. 退出                            │
echo └────────────────────────────────────┘
echo.

choice /c 123456789 /n /m "請選擇 (1-9): "

if errorlevel 9 goto :end
if errorlevel 8 goto :clean_run
if errorlevel 7 goto :clean_dry
if errorlevel 6 goto :merge_run
if errorlevel 5 goto :merge_dry
if errorlevel 4 goto :custom_run
if errorlevel 3 goto :custom_dry
if errorlevel 2 goto :run
if errorlevel 1 goto :dry

:dry
echo.
echo ========================================
echo 整理模式 - 測試運行
echo ========================================
python organize_by_author.py "%DOWNLOAD_PATH%" --dry-run
goto :done

:run
echo.
echo ========================================
echo 整理模式 - 正式執行
echo ========================================
python organize_by_author.py "%DOWNLOAD_PATH%"
goto :done

:custom_dry
echo.
echo ========================================
echo 整理模式 - 自訂路徑測試運行
echo ========================================
set /p CUSTOM_PATH=請輸入下載目錄路徑:
python organize_by_author.py "%CUSTOM_PATH%" --dry-run
goto :done

:custom_run
echo.
echo ========================================
echo 整理模式 - 自訂路徑正式執行
echo ========================================
set /p CUSTOM_PATH=請輸入下載目錄路徑:
python organize_by_author.py "%CUSTOM_PATH%"
goto :done

:merge_dry
echo.
echo ========================================
echo 合併模式 - 測試運行
echo ========================================
echo.
echo 此功能會掃描源目錄中的 [作者名] 目錄，
echo 將其中的漫畫移動到目標目錄對應的 [作者名] 目錄中。
echo 如果目標目錄沒有對應的作者目錄，則跳過。
echo.
set /p SOURCE_PATH=請輸入源目錄路徑:
set /p TARGET_PATH=請輸入目標目錄路徑:
python organize_by_author.py "%SOURCE_PATH%" "%TARGET_PATH%" --merge --dry-run
goto :done

:merge_run
echo.
echo ========================================
echo 合併模式 - 正式執行
echo ========================================
echo.
echo 此功能會掃描源目錄中的 [作者名] 目錄，
echo 將其中的漫畫移動到目標目錄對應的 [作者名] 目錄中。
echo 如果目標目錄沒有對應的作者目錄，則跳過。
echo.
set /p SOURCE_PATH=請輸入源目錄路徑:
set /p TARGET_PATH=請輸入目標目錄路徑:
python organize_by_author.py "%SOURCE_PATH%" "%TARGET_PATH%" --merge
goto :done

:clean_dry
echo.
echo ========================================
echo 清除模式 - 測試運行
echo ========================================
python organize_by_author.py "%DOWNLOAD_PATH%" --clean --dry-run
goto :done

:clean_run
echo.
echo ========================================
echo 清除模式 - 正式執行
echo ========================================
python organize_by_author.py "%DOWNLOAD_PATH%" --clean
goto :done

:done
echo.
pause

:end
