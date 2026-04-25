---
name: YOLO Detector EXE Package Design
description: 将 4_yolo_opencv_detector.ipynb 打包成 exe，添加窗口选择、配置文件、错误处理
type: project
---

# YOLO Detector EXE 打包设计

## 目标

将 `4_yolo_opencv_detector.ipynb` 的检测逻辑打包成独立 exe，添加：
1. 窗口列表选择功能
2. 配置文件持久化
3. 全局错误捕获

## 文件结构

```
detector.py              # 所有逻辑（单文件）
detector_config.json     # 配置文件（自动生成）
build_detector.bat       # 打包脚本
```

## 配置文件格式

```json
{
  "window_name": "",
  "cfg_file": "./yolov4-tiny/yolov4-tiny-custom.cfg",
  "weights_file": "yolov4-tiny-custom_last.weights"
}
```

- `window_name` 为空时，启动时弹出窗口列表选择
- 有值时直接使用上次窗口

## 程序流程

```
启动 → 检查配置文件
     → window_name 为空? → 显示窗口列表 → 用户选择 → 保存配置
     → 加载 YOLO 模型
     → 进入检测循环（try-except 包裹）
        → 截图 → 检测 → 显示结果 + 打印坐标
        → 捕获错误 → 写 error.log + 控制台提示 → 继续
     → 按 'q' 退出
```

## 错误处理

- 主循环 try-except 捕获所有异常
- 写入 `error.log`：时间戳 + 错误类型 + 错误信息
- 控制台打印：`[ERROR] xxx, 继续检测...`
- 不中断程序，继续下一帧

## 打包依赖

- PyInstaller
- pywin32, numpy, Pillow, opencv-python

## 显示方式

- OpenCV 窗口显示检测框（cv.imshow）
- 控制台打印检测坐标
- 按 'q' 退出