# YOLO OpenCV Detector 打包脚本
# 使用 PyInstaller 将 Python 脚本打包成独立的 EXE 文件

# 安装依赖
pip install pyinstaller pywin32 numpy Pillow opencv-python pynput

# 打包步骤 1 - 数据集生成
pyinstaller --onefile ^
    --name "game_capture" ^
    --icon=NONE ^
    --hidden-import=win32gui ^
    --hidden-import=win32ui ^
    --hidden-import=win32con ^
    --hidden-import=PIL ^
    --hidden-import=numpy ^
    --add-data "yolov4-tiny;./yolov4-tiny" ^
    generate_dataset.py

# 清理临时文件
rmdir /s /q build
del /q generate_dataset.spec

echo.
echo 打包完成！EXE 文件位于 dist/game_capture.exe
echo.
echo 使用说明:
echo 1. 将 dist/game_capture.exe 复制到目标电脑
echo 2. 运行 game_capture.exe
echo 3. 输入游戏窗口名称
echo 4. 开始截图
echo.
echo 注意事项:
echo - 需要游戏窗口已经打开
echo - 截图保存在 images 文件夹
echo - 按 Ctrl+C 停止截图
