@echo off
echo ============================================
echo 游戏自动化工具打包脚本
echo ============================================

pyinstaller --onefile ^
    --add-data "yolov4-tiny;yolov4-tiny" ^
    --add-data "yolov4-tiny/obj.names;yolov4-tiny" ^
    --add-data "yolov4-tiny/yolov4-tiny-custom.cfg;yolov4-tiny" ^
    --name "GameAutomate" ^
    game_automate.py

echo ============================================
echo 打包完成! 输出目录: dist/GameAutomate.exe
echo ============================================
pause