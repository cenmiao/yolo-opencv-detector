# YOLO Detector EXE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 4_yolo_opencv_detector.ipynb 的检测逻辑打包成独立 exe，添加窗口选择、配置文件、错误处理功能。

**Architecture:** 单文件 detector.py 包含所有模块（ConfigManager、WindowSelector、WindowCapture、ImageProcessor），配置文件自动管理，全局 try-except 错误捕获。

**Tech Stack:** Python, PyInstaller, OpenCV, pywin32, numpy

---

### Task 1: 创建 detector.py 主文件

**Files:**
- Create: `detector.py`

- [ ] **Step 1: 创建 detector.py 文件框架和导入**

```python
"""
YOLO OpenCV Detector - 实时目标检测工具
打包成 exe 后可独立运行
"""

import json
import os
import sys
import time
import traceback
import numpy as np
import win32gui
import win32ui
import win32con
from PIL import Image
import cv2 as cv

# 配置文件名
CONFIG_FILE = "detector_config.json"
ERROR_LOG_FILE = "error.log"
```

- [ ] **Step 2: 添加 ConfigManager 类**

```python
class ConfigManager:
    """配置文件管理器"""

    DEFAULT_CONFIG = {
        "window_name": "",
        "cfg_file": "./yolov4-tiny/yolov4-tiny-custom.cfg",
        "weights_file": "yolov4-tiny-custom_last.weights"
    }

    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load()

    def load(self):
        """加载配置文件，不存在则创建默认配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] 配置文件读取失败: {e}, 使用默认配置")
                return self.DEFAULT_CONFIG.copy()
        else:
            return self.DEFAULT_CONFIG.copy()

    def save(self):
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()
```

- [ ] **Step 3: 添加 WindowSelector 类**

```python
class WindowSelector:
    """窗口选择器 - 列出所有可见窗口供用户选择"""

    @staticmethod
    def get_visible_windows():
        """获取所有可见窗口列表"""
        windows = []

        def enum_callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # 只保留有标题的窗口
                    windows.append((hwnd, title))
            return True

        win32gui.EnumWindows(enum_callback, None)
        return windows

    @staticmethod
    def select_window():
        """显示窗口列表，让用户选择"""
        windows = WindowSelector.get_visible_windows()

        if not windows:
            print("[ERROR] 未找到任何可见窗口")
            return None

        print("\n===== 可见窗口列表 =====")
        for i, (hwnd, title) in enumerate(windows, 1):
            print(f"  {i}: {title}")

        print("\n请输入窗口编号 (1-{0}), 或输入 0 退出:".format(len(windows)))

        while True:
            try:
                choice = input(">>> ").strip()
                if choice == "0":
                    return None
                idx = int(choice) - 1
                if 0 <= idx < len(windows):
                    selected_title = windows[idx][1]
                    print(f"[INFO] 已选择窗口: {selected_title}")
                    return selected_title
                else:
                    print(f"[WARN] 请输入 1-{len(windows)} 之间的编号")
            except ValueError:
                print("[WARN] 请输入有效的数字")
```

- [ ] **Step 4: 添加 WindowCapture 类**

```python
class WindowCapture:
    """窗口截图类"""

    def __init__(self, window_name):
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise Exception(f'未找到窗口: {window_name}')

        # 获取窗口尺寸并计算去除边框后的实际区域
        window_rect = win32gui.GetWindowRect(self.hwnd)
        self.w = window_rect[2] - window_rect[0]
        self.h = window_rect[3] - window_rect[1]

        # 假设标准边框和标题栏尺寸
        border_pixels = 8
        titlebar_pixels = 30
        self.w = self.w - (border_pixels * 2)
        self.h = self.h - titlebar_pixels - border_pixels
        self.cropped_x = border_pixels
        self.cropped_y = titlebar_pixels

    def get_screenshot(self):
        """截取窗口内容并返回 numpy 数组"""
        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0, 0), (self.w, self.h), dcObj,
                   (self.cropped_x, self.cropped_y), win32con.SRCCOPY)

        signedIntsArray = dataBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (self.h, self.w, 4)

        # 清理资源
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

        # 转换为 RGB
        img = img[..., :3]
        img = np.ascontiguousarray(img)

        return img

    def get_window_size(self):
        return (self.w, self.h)
```

- [ ] **Step 5: 添加 ImageProcessor 类**

```python
class ImageProcessor:
    """YOLO 图像处理器"""

    def __init__(self, img_size, cfg_file, weights_file):
        np.random.seed(42)
        self.net = cv.dnn.readNetFromDarknet(cfg_file, weights_file)
        self.net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)
        self.ln = self.net.getLayerNames()
        self.ln = [self.ln[i - 1] for i in self.net.getUnconnectedOutLayers()]

        self.W = img_size[0]
        self.H = img_size[1]

        # 加载类别名称
        self.classes = {}
        names_file = 'yolov4-tiny/obj.names'
        if os.path.exists(names_file):
            with open(names_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f.readlines()):
                    self.classes[i] = line.strip()
        else:
            # 默认类别（如果文件不存在）
            self.classes = {0: 'object'}

        # 检测框颜色
        self.colors = [
            (0, 0, 255),
            (0, 255, 0),
            (255, 0, 0),
            (255, 255, 0),
            (255, 0, 255),
            (0, 255, 255)
        ]

    def process_image(self, img, confidence=0.5):
        """处理图像并返回检测坐标"""
        blob = cv.dnn.blobFromImage(img, 1/255.0, (416, 416),
                                    swapRB=True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward(self.ln)
        outputs = np.vstack(outputs)

        coordinates = self._get_coordinates(outputs, confidence)
        self._draw_identified_objects(img, coordinates)

        return coordinates

    def _get_coordinates(self, outputs, conf):
        """从输出中提取检测框坐标"""
        boxes = []
        confidences = []
        classIDs = []

        for output in outputs:
            scores = output[5:]
            classID = np.argmax(scores)
            confidence_val = scores[classID]

            if confidence_val > conf:
                x, y, w, h = output[:4] * np.array([self.W, self.H, self.W, self.H])
                p0 = int(x - w//2), int(y - h//2)
                boxes.append([*p0, int(w), int(h)])
                confidences.append(float(confidence_val))
                classIDs.append(classID)

        indices = cv.dnn.NMSBoxes(boxes, confidences, conf, conf - 0.1)

        if len(indices) == 0:
            return []

        coordinates = []
        for i in indices.flatten():
            x, y, w, h = boxes[i][0], boxes[i][1], boxes[i][2], boxes[i][3]
            coordinates.append({
                'x': x, 'y': y, 'w': w, 'h': h,
                'class': classIDs[i],
                'class_name': self.classes.get(classIDs[i], 'unknown')
            })

        return coordinates

    def _draw_identified_objects(self, img, coordinates):
        """在图像上绘制检测框"""
        for coord in coordinates:
            x, y, w, h = coord['x'], coord['y'], coord['w'], coord['h']
            classID = coord['class']
            color = self.colors[classID % len(self.colors)]

            cv.rectangle(img, (x, y), (x + w, y + h), color, 2)
            cv.putText(img, coord['class_name'], (x, y - 10),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        cv.imshow('detector', img)
```

- [ ] **Step 6: 添加错误日志函数**

```python
def log_error(error_msg):
    """将错误写入日志文件"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {error_msg}\n"

    with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

    print(f"[ERROR] {error_msg}, 继续检测...")
```

- [ ] **Step 7: 添加 main() 主函数**

```python
def main():
    """主程序入口"""
    print("===== YOLO OpenCV Detector =====")
    print("按 'q' 键退出检测\n")

    # 加载配置
    config_mgr = ConfigManager()

    # 检查是否需要选择窗口
    window_name = config_mgr.get('window_name', '')

    if not window_name:
        print("[INFO] 配置中没有窗口名称，请选择窗口...")
        window_name = WindowSelector.select_window()

        if not window_name:
            print("[INFO] 用户取消选择，程序退出")
            sys.exit(0)

        # 保存选择的窗口名称
        config_mgr.set('window_name', window_name)
    else:
        print(f"[INFO] 使用上次窗口: {window_name}")
        print("[提示] 如需更换窗口，删除 detector_config.json 重新运行")

    # 初始化窗口截图
    try:
        wincap = WindowCapture(window_name)
        print(f"[INFO] 窗口尺寸: {wincap.get_window_size()}")
    except Exception as e:
        log_error(f"初始化窗口截图失败: {e}")
        sys.exit(1)

    # 初始化 YOLO 检测器
    cfg_file = config_mgr.get('cfg_file')
    weights_file = config_mgr.get('weights_file')

    try:
        improc = ImageProcessor(wincap.get_window_size(), cfg_file, weights_file)
        print(f"[INFO] YOLO 模型加载成功: {weights_file}")
    except Exception as e:
        log_error(f"初始化 YOLO 模型失败: {e}")
        sys.exit(1)

    # 主检测循环
    print("\n[INFO] 开始检测...")
    print("=" * 40)

    while True:
        try:
            # 截图
            screenshot = wincap.get_screenshot()

            # 检测
            coordinates = improc.process_image(screenshot)

            # 打印检测结果
            if coordinates:
                for coord in coordinates:
                    print(f"检测到: {coord['class_name']} @ ({coord['x']}, {coord['y']}) "
                          f"尺寸: {coord['w']}x{coord['h']}")

            # 检查退出键
            if cv.waitKey(1) == ord('q'):
                print("\n[INFO] 用户按下 'q'，退出检测")
                break

        except Exception as e:
            error_detail = f"{type(e).__name__}: {str(e)}"
            log_error(error_detail)
            # 继续下一帧检测，不中断程序
            continue

    # 清理
    cv.destroyAllWindows()
    print("[INFO] 程序结束")


if __name__ == '__main__':
    main()
```

- [ ] **Step 8: 验证 detector.py 文件完整性**

运行语法检查：
```bash
python -m py_compile detector.py
```
Expected: 无错误输出

---

### Task 2: 创建打包脚本 build_detector.bat

**Files:**
- Create: `build_detector.bat`

- [ ] **Step 1: 创建 build_detector.bat 文件**

```batch
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
```

- [ ] **Step 2: 提交文件**

```bash
git add detector.py build_detector.bat docs/superpowers/specs/2026-04-25-detector-exe-design.md docs/superpowers/plans/2026-04-25-detector-exe-implementation.md
git commit -m "feat: add detector.py with window selection, config management and error handling

- Single file detector.py contains all modules
- WindowSelector lists visible windows for user selection
- ConfigManager handles detector_config.json persistence
- Global try-except in main loop with error.log writing
- build_detector.bat for PyInstaller packaging

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: 测试运行

- [ ] **Step 1: 运行 detector.py 测试**

```bash
python detector.py
```

Expected:
- 显示窗口列表
- 用户可选择窗口
- 开始检测循环
- 按 'q' 可退出

- [ ] **Step 2: 检查配置文件生成**

```bash
cat detector_config.json
```

Expected: JSON 文件包含选择的窗口名称

---

### Task 4: 打包验证

- [ ] **Step 1: 执行打包脚本**

```bash
build_detector.bat
```

Expected: 生成 `dist/detector.exe`

- [ ] **Step 2: 测试 exe 运行**

```bash
cd dist
detector.exe
```

Expected: exe 正常运行，窗口选择功能正常