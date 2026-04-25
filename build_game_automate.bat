@echo off
echo ============================================
echo 游戏自动化工具打包脚本
echo ============================================

REM 先打包 exe
pyinstaller --onefile ^
    --name "GameAutomate" ^
    game_automate.py

REM 复制配置文件和权重文件到 dist 目录
echo 复制配置文件到 dist 目录...
xcopy /Y /I yolov4-tiny dist\yolov4-tiny\
copy /Y yolov4-tiny-custom_last.weights dist\yolov4-tiny-custom_last.weights

echo ============================================
echo 打包完成!
echo 输出目录: dist/GameAutomate.exe
echo 配置文件: dist/yolov4-tiny/
echo 权重文件: dist/yolov4-tiny-custom_last.weights
echo ============================================
pause