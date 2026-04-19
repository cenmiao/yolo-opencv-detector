@echo off
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
pyinstaller --onefile ^
    --name "yolo_automate" ^
    --icon=NONE ^
    --hidden-import=win32gui ^
    --hidden-import=win32ui ^
    --hidden-import=win32con ^
    --hidden-import=PIL ^
    --hidden-import=numpy ^
    --hidden-import=cv2 ^
    --hidden-import=pynput ^
    --add-data "yolov4-tiny;./yolov4-tiny" ^
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
echo 输出文件：dist/yolo_automate.exe
echo.
echo 使用说明:
echo 1. 将以下文件复制到目标目录:
echo    - dist/yolo_automate.exe
echo    - yolov4-tiny-custom.cfg
echo    - yolov4-tiny-custom_last.weights
echo    - yolov4-tiny/obj.names
echo 2. 运行 yolo_automate.exe
echo 3. 按照提示配置窗口、模型文件和自动化参数
echo 4. 程序会自动保存配置到 runtime-config.json
echo.
echo 注意事项:
echo - 需要游戏窗口已经打开
echo - 按 'q' 键退出
echo - 按 'v' 键切换可视化窗口
echo.
