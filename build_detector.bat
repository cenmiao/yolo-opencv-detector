@echo off
echo ===== YOLO Detector 打包脚本 =====
echo.

REM 检查 PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] 安装 PyInstaller...
    pip install pyinstaller
)

REM 安装依赖
echo [INFO] 安装依赖...
pip install pywin32 numpy Pillow opencv-python

REM 打包
echo [INFO] 开始打包...
pyinstaller --onefile ^
    --name "detector" ^
    --console ^
    --hidden-import=win32gui ^
    --hidden-import=win32ui ^
    --hidden-import=win32con ^
    --hidden-import=PIL ^
    --hidden-import=numpy ^
    --hidden-import=cv2 ^
    --add-data "yolov4-tiny;yolov4-tiny" ^
    detector.py

REM 清理临时文件
echo [INFO] 清理临时文件...
rmdir /s /q build 2>nul
del /q detector.spec 2>nul

echo.
echo ===== 打包完成 =====
echo EXE 文件: dist\detector.exe
echo.
echo 使用说明:
echo 1. 将 dist\detector.exe 复制到目标电脑
echo 2. 确保 yolov4-tiny 目录和 weights 文件在同级目录
echo 3. 运行 detector.exe
echo 4. 选择窗口开始检测
echo.
pause
