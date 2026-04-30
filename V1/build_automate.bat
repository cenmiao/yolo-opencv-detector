@echo off
chcp 65001 >nul
echo ==================================================
echo YOLO OpenCV 自动化工具 - 打包脚本
echo ==================================================
echo.

REM 安装依赖
echo [1/3] 安装依赖...
pip install pyinstaller pywin32 numpy Pillow opencv-python pynput
echo.

REM 打包
echo [2/3] 打包 yolo_automate.py...
pyinstaller --onefile --name "yolo_automate" ^
    --hidden-import=win32gui ^
    --hidden-import=win32ui ^
    --hidden-import=win32con ^
    --hidden-import=PIL ^
    --hidden-import=numpy ^
    --hidden-import=cv2 ^
    --hidden-import=pynput ^
    yolo_automate.py

echo.
echo [3/3] 清理临时文件...
rmdir /s /q build
del /q yolo_automate.spec

echo.
echo ==================================================
echo 打包完成!
echo ==================================================
echo.
echo 输出文件：dist\yolo_automate.exe
echo.
echo 使用说明:
echo 将以下文件复制到目标目录:
echo    - dist\yolo_automate.exe
echo    - yolov4-tiny-custom.cfg
echo    - yolov4-tiny-custom_last.weights
echo    - yolov4-tiny\obj.names
echo.
echo 运行 yolo_automate.exe 即可启动程序
echo.
