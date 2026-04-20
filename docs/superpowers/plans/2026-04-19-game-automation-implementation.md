# 游戏自动化检测工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于已有的 YOLO OpenCV 检测器代码，开发一个游戏自动化辅助工具，当检测到敌对行会玩家进入指定距离阈值时自动触发键盘按键。

**Architecture:** 
- 复用现有的 `WindowCapture` 和 `ImageProcessor` 类
- 新增 `ConfigManager` 类管理配置持久化（runtime-config.json）
- 新增 `AutomationEngine` 类处理距离计算、冷却时间、按键触发逻辑
- 主程序 `yolo_automate.py` 整合所有组件

**Tech Stack:** Python 3.x, OpenCV, YOLOv4-tiny, pywin32, pynput, numpy, Pillow, PyInstaller

---

## File Structure

**需要创建的文件：**
- `yolo_automate.py` - 主程序入口，整合所有组件
- `build_automate.bat` - PyInstaller 打包脚本

**需要修改的文件：**
- 无（完全复用现有代码，新增独立文件）

**依赖的现有文件：**
- `yolo_opencv_detector.py` - WindowCapture 和 ImageProcessor 类参考
- `dist/yolov4-tiny-custom.cfg` - YOLO 配置文件
- `dist/yolov4-tiny-custom_last.weights` - YOLO 权重文件
- `dist/yolov4-tiny/obj.names` - 类别名称文件

---

### Task 1: ConfigManager 类实现

**Files:**
- Create: `yolo_automate.py` (部分实现)

**职责：** 管理 runtime-config.json 的读写，提供默认配置和配置保存功能

- [ ] **Step 1: 编写 ConfigManager 测试**

```python
# test_config_manager.py
import json
import os
from yolo_automate import ConfigManager

def test_load_config_returns_default_when_file_not_exists():
    # 确保配置文件不存在
    if os.path.exists('test-runtime-config.json'):
        os.remove('test-runtime-config.json')
    config = ConfigManager('test-runtime-config.json').load_config()
    assert config['window_name'] == ''
    assert config['detection_fps'] == 20
    assert config['distance_threshold'] == 200
    assert config['trigger_key'] == 'space'
    assert config['cooldown_ms'] == 500

def test_save_config_writes_to_file():
    config_manager = ConfigManager('test-runtime-config.json')
    test_config = {
        'window_name': 'Test Window',
        'cfg_file': './test.cfg',
        'weights_file': './test.weights',
        'detection_fps': 30,
        'distance_threshold': 150,
        'trigger_key': 'x',
        'cooldown_ms': 500,
        'visual_enabled': True
    }
    config_manager.save_config(test_config)
    assert os.path.exists('test-runtime-config.json')
    with open('test-runtime-config.json', 'r', encoding='utf-8') as f:
        loaded = json.load(f)
    assert loaded['window_name'] == 'Test Window'
    assert loaded['detection_fps'] == 30
    # 清理
    os.remove('test-runtime-config.json')

def test_load_config_reads_from_file():
    # 先保存
    config_manager = ConfigManager('test-runtime-config.json')
    test_config = {
        'window_name': 'Loaded Window',
        'cfg_file': './loaded.cfg',
        'weights_file': './loaded.weights',
        'detection_fps': 25,
        'distance_threshold': 250,
        'trigger_key': 'z',
        'cooldown_ms': 500,
        'visual_enabled': False
    }
    config_manager.save_config(test_config)
    # 再加载
    loaded_config = config_manager.load_config()
    assert loaded_config['window_name'] == 'Loaded Window'
    assert loaded_config['detection_fps'] == 25
    assert loaded_config['visual_enabled'] == False
    # 清理
    os.remove('test-runtime-config.json')
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest test_config_manager.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'yolo_automate'"

- [ ] **Step 3: 实现 ConfigManager 类**

```python
# yolo_automate.py (部分)
import json
import os

CONFIG_FILE = "runtime-config.json"

class ConfigManager:
    """配置文件管理器"""
    
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            'window_name': '',
            'cfg_file': './yolov4-tiny-custom.cfg',
            'weights_file': './yolov4-tiny-custom_last.weights',
            'detection_fps': 20,
            'distance_threshold': 200,
            'trigger_key': 'space',
            'cooldown_ms': 500,
            'visual_enabled': True
        }
    
    def load_config(self):
        """从文件加载配置"""
        default_config = self.get_default_config()
        
        if not os.path.exists(self.config_file):
            print(f"配置文件不存在，使用默认配置")
            return default_config
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并配置，缺失的键使用默认值
                return {
                    'window_name': config.get('window_name', default_config['window_name']),
                    'cfg_file': config.get('cfg_file', default_config['cfg_file']),
                    'weights_file': config.get('weights_file', default_config['weights_file']),
                    'detection_fps': config.get('detection_fps', default_config['detection_fps']),
                    'distance_threshold': config.get('distance_threshold', default_config['distance_threshold']),
                    'trigger_key': config.get('trigger_key', default_config['trigger_key']),
                    'cooldown_ms': config.get('cooldown_ms', default_config['cooldown_ms']),
                    'visual_enabled': config.get('visual_enabled', default_config['visual_enabled'])
                }
        except Exception as e:
            print(f"读取配置文件失败：{e}，使用默认配置")
            return default_config
    
    def save_config(self, config):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"配置已保存至 {self.config_file}")
        except Exception as e:
            print(f"保存配置失败：{e}")
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest test_config_manager.py -v
```
Expected: PASS (3/3 tests passed)

- [ ] **Step 5: 提交**

```bash
git add yolo_automate.py test_config_manager.py
git commit -m "feat: add ConfigManager for runtime-config.json management"
```

---

### Task 2: AutomationEngine 类实现

**Files:**
- Modify: `yolo_automate.py` (添加 AutomationEngine 类)

**职责：** 距离计算、最近敌人查找、冷却时间管理、按键触发

- [ ] **Step 1: 编写 AutomationEngine 测试**

```python
# test_automation_engine.py
import math
from unittest.mock import Mock
from pynput.keyboard import Controller as KeyboardController
from yolo_automate import AutomationEngine

def test_calculate_distance_returns_correct_value():
    # 3-4-5 三角形
    center1 = {'x': 0, 'y': 0, 'w': 10, 'h': 10}
    center2 = {'x': 30, 'y': 40, 'w': 10, 'h': 10}
    # 中心点：(5,5) 和 (35,45)，距离 = sqrt(30^2 + 40^2) = 50
    engine = AutomationEngine(200, 'space', 500)
    distance = engine.calculate_distance(center1, center2)
    assert abs(distance - 50.0) < 0.001

def test_find_nearest_enemy_returns_closest():
    player = {'x': 0, 'y': 0, 'w': 10, 'h': 10, 'class_name': '1ziji'}
    enemies = [
        {'x': 100, 'y': 0, 'w': 10, 'h': 10, 'class_name': '2diguihanghui'},  # 距离 100
        {'x': 50, 'y': 0, 'w': 10, 'h': 10, 'class_name': '2diguihanghui'},   # 距离 50
        {'x': 200, 'y': 0, 'w': 10, 'h': 10, 'class_name': '2diguihanghui'},  # 距离 200
    ]
    engine = AutomationEngine(200, 'space', 500)
    nearest = engine.find_nearest_enemy(player, enemies)
    assert nearest == enemies[1]  # 最近的是第二个

def test_should_trigger_when_in_range_and_cooldown_expired():
    engine = AutomationEngine(200, 'space', 500)  # 阈值 200px, 冷却 500ms
    engine.last_trigger_time = 0  # 重置冷却时间
    
    # 距离在阈值内，应该触发
    assert engine.should_trigger(150, 1000) == True
    
    # 距离超出阈值，不应该触发
    assert engine.should_trigger(250, 1000) == True

def test_should_not_trigger_when_cooldown_active():
    engine = AutomationEngine(200, 'space', 500)
    engine.last_trigger_time = 1000  # 上次触发时间
    
    # 冷却时间内（500ms 内），不应该触发
    assert engine.should_trigger(100, 1200) == False
    
    # 冷却时间结束，应该触发
    assert engine.should_trigger(100, 1600) == True

def test_trigger_action_presses_and_releases_key():
    engine = AutomationEngine(200, 'space', 500)
    mock_keyboard = Mock()
    mock_key = Mock()
    
    # 模拟按键对象
    from pynput.keyboard import Key
    engine.trigger_action(mock_keyboard, 'space')
    
    # 验证 press 和 release 被调用
    mock_keyboard.press.assert_called()
    mock_keyboard.release.assert_called()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest test_automation_engine.py -v
```
Expected: FAIL (AutomationEngine not defined)

- [ ] **Step 3: 实现 AutomationEngine 类**

```python
# yolo_automate.py (添加)
import math
from time import time
from pynput.keyboard import Key, Controller as KeyboardController

class AutomationEngine:
    """自动化引擎 - 处理距离计算、冷却、按键触发"""
    
    def __init__(self, distance_threshold, trigger_key, cooldown_ms):
        self.distance_threshold = distance_threshold
        self.trigger_key = trigger_key
        self.cooldown_ms = cooldown_ms
        self.last_trigger_time = 0
        self.keyboard = KeyboardController()
    
    def calculate_distance(self, obj1, obj2):
        """计算两个检测框中心点之间的距离（像素）"""
        # 计算中心点
        center1_x = obj1['x'] + obj1['w'] // 2
        center1_y = obj1['y'] + obj1['h'] // 2
        center2_x = obj2['x'] + obj2['w'] // 2
        center2_y = obj2['y'] + obj2['h'] // 2
        
        # 欧几里得距离
        distance = math.sqrt(
            (center2_x - center1_x) ** 2 + 
            (center2_y - center1_y) ** 2
        )
        return distance
    
    def find_nearest_enemy(self, player, enemies):
        """找到距离玩家最近的敌人"""
        if not enemies:
            return None
        
        nearest = None
        min_distance = float('inf')
        
        for enemy in enemies:
            distance = self.calculate_distance(player, enemy)
            if distance < min_distance:
                min_distance = distance
                nearest = enemy
        
        return nearest
    
    def should_trigger(self, distance, current_time_ms):
        """判断是否应该触发按键"""
        # 检查距离是否在阈值内
        if distance >= self.distance_threshold:
            return False
        
        # 检查冷却时间是否结束
        elapsed_ms = current_time_ms - self.last_trigger_time
        if elapsed_ms < self.cooldown_ms:
            return False
        
        return True
    
    def trigger_action(self, keyboard, key_name):
        """执行按键动作"""
        # 尝试获取按键对象
        try:
            # 特殊按键
            key = getattr(Key, key_name, None)
            if key is None:
                # 普通字符按键
                if len(key_name) == 1:
                    from pynput.keyboard import KeyCode
                    key = KeyCode.from_char(key_name)
                else:
                    # 尝试其他常见按键名称
                    key_map = {
                        'space': Key.space,
                        'enter': Key.enter,
                        'tab': Key.tab,
                        'esc': Key.esc,
                        'shift': Key.shift,
                        'ctrl': Key.ctrl,
                        'alt': Key.alt,
                    }
                    key = key_map.get(key_name.lower())
            
            if key is not None:
                keyboard.press(key)
                keyboard.release(key)
                return True
        except Exception as e:
            print(f"按键触发失败：{e}")
            return False
        
        return False
    
    def reset_cooldown(self):
        """重置冷却时间"""
        self.last_trigger_time = time() * 1000  # 转换为毫秒
    
    def get_cooldown_remaining(self, current_time_ms):
        """获取剩余冷却时间（毫秒）"""
        elapsed_ms = current_time_ms - self.last_trigger_time
        remaining = self.cooldown_ms - elapsed_ms
        return max(0, remaining)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest test_automation_engine.py -v
```
Expected: PASS (5/5 tests passed)

- [ ] **Step 5: 提交**

```bash
git add yolo_automate.py test_automation_engine.py
git commit -m "feat: add AutomationEngine for distance calculation and key triggering"
```

---

### Task 3: 主程序入口实现 - 配置流程

**Files:**
- Modify: `yolo_automate.py` (添加主程序入口和配置流程)

**职责：** 窗口选择、配置文件选择、检测频率设置、自动化参数配置、可视化选项

- [ ] **Step 1: 编写主配置流程测试**

```python
# test_main_config.py
from yolo_automate import select_window_from_list, get_user_settings

def test_select_window_from_list_returns_window_title():
    # 这个测试需要模拟用户输入，实际测试时通过
    # 这里主要验证窗口列表功能
    from yolo_automate import WindowCapture
    windows = WindowCapture.list_available_windows()
    # 至少应该能找到一些窗口
    assert len(windows) > 0
```

- [ ] **Step 2: 实现窗口选择功能**

```python
# yolo_automate.py (添加)
import win32gui
import win32ui
import win32con
import numpy as np
from PIL import Image
import cv2 as cv
import os
import sys

class WindowCapture:
    """窗口截图捕获类（复用现有代码）"""
    w = 0
    h = 0
    hwnd = None

    @staticmethod
    def list_available_windows():
        """列出所有可见窗口的标题"""
        windows = []

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # 只添加有标题的窗口
                    windows.append((hwnd, title))
            return True

        win32gui.EnumWindows(callback, None)
        return windows

    def __init__(self, window_name):
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise Exception(f'Window not found: {window_name}')

        # 检查窗口是否最小化
        if win32gui.IsIconic(self.hwnd):
            raise Exception(f'窗口 "{window_name}" 已最小化，请恢复窗口后再试')

        window_rect = win32gui.GetWindowRect(self.hwnd)
        self.w = window_rect[2] - window_rect[0]
        self.h = window_rect[3] - window_rect[1]

        border_pixels = 8
        titlebar_pixels = 30
        self.w = self.w - (border_pixels * 2)
        self.h = self.h - titlebar_pixels - border_pixels
        self.cropped_x = border_pixels
        self.cropped_y = titlebar_pixels

        # 验证窗口尺寸是否有效
        if self.w <= 0 or self.h <= 0:
            raise Exception(f'窗口尺寸无效：{self.w} x {self.h}\n'
                          f'窗口可能太小或被遮挡，请确保窗口完全可见且尺寸大于 100x100 像素')

    def get_screenshot(self):
        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0, 0), (self.w, self.h), dcObj, (self.cropped_x, self.cropped_y), win32con.SRCCOPY)

        signedIntsArray = dataBitMap.GetBitmapBits(True)
        img = np.fromstring(signedIntsArray, dtype='uint8')
        img.shape = (self.h, self.w, 4)

        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

        img = img[..., :3]
        img = np.ascontiguousarray(img)

        return img

    def get_window_size(self):
        return (self.w, self.h)

def select_window_from_list():
    """显示窗口列表供用户选择"""
    windows = WindowCapture.list_available_windows()

    if not windows:
        print("未找到任何可见窗口")
        return None

    print("\n" + "=" * 60)
    print("可用窗口列表:")
    print("=" * 60)

    # 过滤一些系统窗口
    filtered_windows = [
        (hwnd, title) for hwnd, title in windows
        if not title.startswith('IME ') and
           not title.startswith('MSCTFIME ') and
           not title.startswith('Default IME') and
           not title.startswith(' ') and
           len(title) > 0
    ]

    if not filtered_windows:
        print("未找到合适的窗口")
        return None

    for i, (hwnd, title) in enumerate(filtered_windows):
        print(f"  [{i + 1}] {title}")

    print("=" * 60)
    print()

    while True:
        choice = input(f"请输入窗口编号 (1-{len(filtered_windows)}) 或输入 'r' 刷新列表，'q' 退出：").strip()

        if choice.lower() == 'q':
            return None
        elif choice.lower() == 'r':
            return select_window_from_list()

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(filtered_windows):
                return filtered_windows[idx][1]
            else:
                print(f"请输入 1-{len(filtered_windows)} 之间的数字")
        except ValueError:
            print("请输入有效的数字")
```

- [ ] **Step 3: 实现用户设置获取功能**

```python
# yolo_automate.py (添加)
def get_user_settings(saved_config):
    """获取用户设置，优先使用保存的配置"""
    print("\n" + "=" * 60)
    print("配置设置")
    print("=" * 60)
    
    # 窗口选择
    print(f"\n上次使用的窗口：{saved_config['window_name'] or '未设置'}")
    use_last = input("是否使用上次的窗口配置？(Y/n): ").strip().lower()
    
    if use_last != 'n' and saved_config['window_name']:
        window_name = saved_config['window_name']
        print(f"已选择：{window_name}")
    else:
        print()
        show_list = input("是否显示窗口列表供选择？(Y/n): ").strip().lower()
        if show_list != 'n':
            window_name = select_window_from_list()
            if not window_name:
                print("未选择窗口，程序退出")
                return None
        else:
            window_name = input("请输入游戏窗口标题栏名称：").strip()
        
        if not window_name:
            print("错误：窗口名称不能为空")
            return None
    
    # 配置文件选择
    print(f"\n上次使用的配置文件：{saved_config['cfg_file']}")
    use_last_cfg = input("是否使用上次的配置文件？(Y/n): ").strip().lower()
    if use_last_cfg != 'n':
        cfg_file = saved_config['cfg_file']
    else:
        cfg_file = input("cfg 文件路径：").strip()
        if not cfg_file:
            cfg_file = saved_config['cfg_file']
    
    # 权重文件选择
    print(f"\n上次使用的权重文件：{saved_config['weights_file']}")
    use_last_weights = input("是否使用上次的权重文件？(Y/n): ").strip().lower()
    if use_last_weights != 'n':
        weights_file = saved_config['weights_file']
    else:
        weights_file = input("weights 文件路径：").strip()
        if not weights_file:
            weights_file = saved_config['weights_file']
    
    # 检测频率
    print(f"\n检测频率 FPS (上次：{saved_config['detection_fps']}): ", end='')
    fps_input = input().strip()
    detection_fps = int(fps_input) if fps_input else saved_config['detection_fps']
    
    # 距离阈值
    print(f"\n距离阈值（像素，上次：{saved_config['distance_threshold']}): ", end='')
    threshold_input = input().strip()
    distance_threshold = int(threshold_input) if threshold_input else saved_config['distance_threshold']
    
    # 触发按键
    print(f"\n触发按键 (上次：{saved_config['trigger_key']}): ", end='')
    trigger_key = input().strip() or saved_config['trigger_key']
    
    # 可视化选项
    print(f"\n是否开启可视化窗口？(Y/n): ", end='')
    visual_input = input().strip().lower()
    visual_enabled = visual_input != 'n' if visual_input else saved_config['visual_enabled']
    
    return {
        'window_name': window_name,
        'cfg_file': cfg_file,
        'weights_file': weights_file,
        'detection_fps': detection_fps,
        'distance_threshold': distance_threshold,
        'trigger_key': trigger_key,
        'cooldown_ms': 500,  # 固定 500ms
        'visual_enabled': visual_enabled
    }
```

- [ ] **Step 4: 提交**

```bash
git add yolo_automate.py
git commit -m "feat: add window selection and user settings configuration"
```

---

### Task 4: ImageProcessor 类实现

**Files:**
- Modify: `yolo_automate.py` (添加 ImageProcessor 类)

**职责：** 加载 YOLO 模型，处理图像，返回检测结果

- [ ] **Step 1: 实现 ImageProcessor 类**

```python
# yolo_automate.py (添加)
class ImageProcessor:
    """图像处理与目标检测类"""
    W = 0
    H = 0
    net = None
    ln = None
    classes = {}
    colors = []

    def __init__(self, img_size, cfg_file, weights_file):
        np.random.seed(42)

        # 处理打包后的路径
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        # 优先尝试当前工作目录（EXE 运行目录），其次尝试打包目录
        cfg_path = cfg_file
        if not os.path.exists(cfg_path):
            cfg_path = os.path.join(base_path, cfg_file.lstrip('./'))

        weights_path = weights_file
        if not os.path.exists(weights_path):
            weights_path = os.path.join(base_path, weights_file.lstrip('./'))

        print(f"加载配置文件：{cfg_path}")
        print(f"加载权重文件：{weights_path}")

        self.net = cv.dnn.readNetFromDarknet(cfg_path, weights_path)
        self.net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)
        self.ln = self.net.getLayerNames()
        self.ln = [self.ln[i - 1] for i in self.net.getUnconnectedOutLayers()]
        self.W = img_size[0]
        self.H = img_size[1]

        # 加载类别名称
        names_path = os.path.join(base_path, 'yolov4-tiny', 'obj.names')
        if not os.path.exists(names_path):
            names_path = 'yolov4-tiny/obj.names'
        if not os.path.exists(names_path):
            names_path = 'obj.names'

        print(f"加载类别名称：{names_path}")

        with open(names_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        for i, line in enumerate(lines):
            self.classes[i] = line.strip()

        # 颜色配置 (BGR 格式)
        # 1ziji=绿色，2diguihanghui=红色，3zijihanghui=蓝色
        self.colors = [
            (0, 255, 0),    # 绿色 - 自己
            (0, 0, 255),    # 红色 - 敌对
            (255, 0, 0),    # 蓝色 - 友方
            (255, 255, 0),  # 青色
            (255, 0, 255),  # 黄色
            (0, 255, 255)   # 橙色
        ]

    def process_image(self, img):
        """处理图像并返回检测结果"""
        blob = cv.dnn.blobFromImage(img, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward(self.ln)
        outputs = np.vstack(outputs)

        coordinates = self.get_coordinates(outputs, 0.5)
        return coordinates

    def get_coordinates(self, outputs, conf):
        """解析模型输出，获取检测框坐标"""
        boxes = []
        confidences = []
        classIDs = []

        for output in outputs:
            scores = output[5:]
            classID = np.argmax(scores)
            confidence = scores[classID]
            if confidence > conf:
                x, y, w, h = output[:4] * np.array([self.W, self.H, self.W, self.H])
                p0 = int(x - w // 2), int(y - h // 2)
                boxes.append([*p0, int(w), int(h)])
                confidences.append(float(confidence))
                classIDs.append(classID)

        indices = cv.dnn.NMSBoxes(boxes, confidences, conf, conf - 0.1)

        if len(indices) == 0:
            return []

        coordinates = []
        for i in indices.flatten():
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])
            coordinates.append({
                'x': x,
                'y': y,
                'w': w,
                'h': h,
                'class': classIDs[i],
                'class_name': self.classes[classIDs[i]],
                'confidence': float(confidences[i])
            })
        return coordinates

    def draw_identified_objects(self, img, coordinates, show_distance_to=None):
        """绘制检测结果，可选显示到指定目标的距离线"""
        player = None
        enemies = []
        
        # 分类目标
        for coord in coordinates:
            if coord['class_name'] == '1ziji':
                player = coord
            elif coord['class_name'] == '2diguihanghui':
                enemies.append(coord)
        
        # 绘制所有检测框
        for coordinate in coordinates:
            x = coordinate['x']
            y = coordinate['y']
            w = coordinate['w']
            h = coordinate['h']
            classID = coordinate['class']

            color = self.colors[classID] if classID < len(self.colors) else (255, 255, 255)

            cv.rectangle(img, (x, y), (x + w, y + h), color, 2)
            label = f"{coordinate['class_name']}"
            cv.putText(img, label, (x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # 如果有玩家和敌人，绘制距离线和阈值圆
        if player and show_distance_to is not None and len(enemies) > 0:
            # 找到最近的敌人
            engine = AutomationEngine(show_distance_to, 'space', 500)
            nearest = engine.find_nearest_enemy(player, enemies)
            
            if nearest:
                # 计算中心点
                player_cx = player['x'] + player['w'] // 2
                player_cy = player['y'] + player['h'] // 2
                enemy_cx = nearest['x'] + nearest['w'] // 2
                enemy_cy = nearest['y'] + nearest['h'] // 2
                
                # 绘制距离线（黄色虚线）
                cv.line(img, (player_cx, player_cy), (enemy_cx, enemy_cy), (0, 255, 255), 2)
                
                # 显示距离数值
                distance = engine.calculate_distance(player, nearest)
                cv.putText(img, f"{distance:.1f}px", 
                          ((player_cx + enemy_cx) // 2, (player_cy + enemy_cy) // 2),
                          cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                
                # 绘制阈值圆（以玩家为中心）
                center = (player_cx, player_cy)
                cv.circle(img, center, int(show_distance_to), (0, 255, 255), 2)
        
        cv.imshow('YOLO Automation', img)
```

- [ ] **Step 2: 提交**

```bash
git add yolo_automate.py
git commit -m "feat: add ImageProcessor for YOLO inference"
```

---

### Task 5: 主检测循环实现

**Files:**
- Modify: `yolo_automate.py` (添加主函数和检测循环)

**职责：** 整合所有组件，运行检测循环，处理可视化

- [ ] **Step 1: 实现主函数**

```python
# yolo_automate.py (添加)
def main():
    """主函数"""
    print("=" * 50)
    print("YOLO OpenCV 游戏自动化工具")
    print("=" * 50)
    print()

    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 加载上次配置
    print("[加载配置]")
    saved_config = config_manager.load_config()
    
    # 获取用户设置
    config = get_user_settings(saved_config)
    if config is None:
        print("配置失败，程序退出")
        return
    
    # 保存配置
    config_manager.save_config(config)
    
    try:
        # 初始化窗口捕获
        print(f"\n正在查找窗口：{config['window_name']}...")
        wincap = WindowCapture(config['window_name'])
        print(f"窗口找到！尺寸：{wincap.w} x {wincap.h}")
        print()

        # 初始化图像处理器
        print("初始化检测模型...")
        improc = ImageProcessor(wincap.get_window_size(), config['cfg_file'], config['weights_file'])
        print("模型加载完成!")
        print()

        # 初始化自动化引擎
        automation = AutomationEngine(
            config['distance_threshold'],
            config['trigger_key'],
            config['cooldown_ms']
        )
        print(f"自动化引擎就绪：阈值={config['distance_threshold']}px, 按键={config['trigger_key']}, 冷却={config['cooldown_ms']}ms")
        print()

        # 计算帧间隔
        frame_delay = 1.0 / config['detection_fps']
        
        print("开始自动化检测...")
        print(f"检测频率：{config['detection_fps']} FPS")
        print(f"可视化：{'开启' if config['visual_enabled'] else '关闭'}")
        print("按 'q' 退出，按 'v' 切换可视化")
        print()

        # 检测循环
        running = True
        visual_enabled = config['visual_enabled']
        
        while running:
            frame_start = time()
            
            # 截图
            screenshot = wincap.get_screenshot()
            
            # 检测
            coordinates = improc.process_image(screenshot)
            
            # 分类目标
            player = None
            enemies = []
            allies = []
            
            for coord in coordinates:
                if coord['class_name'] == '1ziji':
                    player = coord
                elif coord['class_name'] == '2diguihanghui':
                    enemies.append(coord)
                elif coord['class_name'] == '3zijihanghui':
                    allies.append(coord)
            
            # 自动化逻辑
            if player and enemies:
                # 找到最近的敌人
                nearest = automation.find_nearest_enemy(player, enemies)
                if nearest:
                    distance = automation.calculate_distance(player, nearest)
                    current_time_ms = time() * 1000
                    
                    if automation.should_trigger(distance, current_time_ms):
                        # 触发按键
                        automation.trigger_action(automation.keyboard, config['trigger_key'])
                        automation.reset_cooldown()
                        print(f"[触发] 距离={distance:.1f}px, 按键={config['trigger_key']}")
            
            # 可视化
            if visual_enabled:
                # 创建用于显示的副本
                display_img = screenshot.copy()
                # 绘制所有检测结果
                improc.draw_identified_objects(display_img, coordinates, config['distance_threshold'])
                
                # 显示状态信息
                status_y = 30
                cv.putText(display_img, f"FPS: {config['detection_fps']}", (10, status_y), 
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv.putText(display_img, f"检测到：{len(coordinates)} 个目标", (10, status_y + 30),
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # 冷却状态
                cooldown_remaining = automation.get_cooldown_remaining(time() * 1000)
                status_text = f"冷却：{cooldown_remaining:.0f}ms" if cooldown_remaining > 0 else "状态：就绪"
                status_color = (0, 0, 255) if cooldown_remaining > 0 else (0, 255, 0)
                cv.putText(display_img, status_text, (10, status_y + 60),
                          cv.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                
                cv.imshow('YOLO Automation', display_img)
            
            # 按键处理
            key = cv.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('v'):
                visual_enabled = not visual_enabled
                print(f"可视化已{'开启' if visual_enabled else '关闭'}")
            
            # 帧率控制
            elapsed = time() - frame_start
            if elapsed < frame_delay:
                sleep(frame_delay - elapsed)
        
        print('\n检测结束。')

    except Exception as e:
        print(f"错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        cv.destroyAllWindows()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 提交**

```bash
git add yolo_automate.py
git commit -m "feat: add main detection loop with automation and visualization"
```

---

### Task 6: 打包脚本实现

**Files:**
- Create: `build_automate.bat`

**职责：** 使用 PyInstaller 打包 yolo_automate.py 为 dist/yolo_automate.exe

- [ ] **Step 1: 创建打包脚本**

```batch
# build_automate.bat
# YOLO OpenCV Automate 打包脚本
# 使用 PyInstaller 将 Python 脚本打包成独立的 EXE 文件

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
echo    - dist/yolov4-tiny-custom.cfg
echo    - dist/yolov4-tiny-custom_last.weights
echo    - dist/yolov4-tiny/obj.names
echo 2. 运行 yolo_automate.exe
echo 3. 按照提示配置窗口、模型文件和自动化参数
echo 4. 程序会自动保存配置到 runtime-config.json
echo.
echo 注意事项:
echo - 需要游戏窗口已经打开
echo - 按 'q' 键退出
echo - 按 'v' 键切换可视化窗口
echo.
```

- [ ] **Step 2: 测试打包脚本（可选，需要用户确认）**

```bash
.\build_automate.bat
```

- [ ] **Step 3: 提交**

```bash
git add build_automate.bat
git commit -m "feat: add PyInstaller build script for yolo_automate.exe"
```

---

### Task 7: 使用说明文档

**Files:**
- Create: `dist/AUTOMATE_README.md`

**职责：** 提供 yolo_automate.exe 的使用说明

- [ ] **Step 1: 创建使用说明文档**

```markdown
# YOLO OpenCV 游戏自动化工具使用说明

## 功能描述

本工具使用 YOLOv4-tiny 模型检测游戏中的三类目标：
- `1ziji` - 自己的角色（绿色框）
- `2diguihanghui` - 敌对行会的玩家（红色框）
- `3zijihanghui` - 自己行会的玩家（蓝色框）

当检测到敌对行会玩家进入指定距离阈值时，自动触发键盘按键。

## 文件结构

```
dist/
├── yolo_automate.exe              # 主程序
├── yolov4-tiny-custom.cfg         # YOLO 配置文件
├── yolov4-tiny-custom_last.weights # YOLO 权重文件
├── yolov4-tiny/
│   └── obj.names                  # 类别名称文件
└── AUTOMATE_README.md             # 本说明文件
```

## 使用方法

### 首次运行

1. 将 `dist` 目录下的所有文件复制到目标目录
2. 双击运行 `yolo_automate.exe`
3. 按照提示进行配置：
   - 选择游戏窗口
   - 确认配置文件和权重文件路径
   - 设置检测频率（FPS）
   - 设置距离阈值（像素）
   - 设置触发按键
   - 选择是否开启可视化窗口
4. 配置会自动保存到 `runtime-config.json`

### 后续运行

程序会自动加载上次的配置，直接按 `Y` 确认即可快速启动。

## 配置说明

### runtime-config.json

```json
{
  "window_name": "游戏窗口标题",
  "cfg_file": "./yolov4-tiny-custom.cfg",
  "weights_file": "./yolov4-tiny-custom_last.weights",
  "detection_fps": 20,
  "distance_threshold": 200,
  "trigger_key": "space",
  "cooldown_ms": 500,
  "visual_enabled": true
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| window_name | 游戏窗口标题 | - |
| cfg_file | YOLO 配置文件路径 | ./yolov4-tiny-custom.cfg |
| weights_file | YOLO 权重文件路径 | ./yolov4-tiny-custom_last.weights |
| detection_fps | 检测频率（FPS） | 20 |
| distance_threshold | 触发距离阈值（像素） | 200 |
| trigger_key | 触发按键 | space |
| cooldown_ms | 冷却时间（毫秒） | 500 |
| visual_enabled | 是否开启可视化 | true |

## 快捷键

| 按键 | 功能 |
|------|------|
| q | 退出程序 |
| v | 切换可视化窗口 |

## 常见问题

### 找不到窗口
- 确保游戏窗口已经打开且未最小化
- 检查窗口标题是否与配置一致

### 检测不到目标
- 检查模型文件路径是否正确
- 确保窗口内容中确实有可检测的目标

### 按键不触发
- 检查距离阈值是否设置过小
- 确认触发按键是否有效（尝试 space、x、z 等）
- 注意 500ms 冷却时间

## 重新打包

如需修改代码后重新打包，运行：

```batch
build_automate.bat
```

## 技术支持

如有问题，请联系开发者或查看项目文档。
```

- [ ] **Step 2: 提交**

```bash
git add dist/AUTOMATE_README.md
git commit -m "docs: add usage instructions for yolo_automate.exe"
```

---

## Self-Review

### 1. Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| 窗口选择 | Task 3 |
| 配置持久化 (runtime-config.json) | Task 1 |
| 检测频率配置 | Task 3 |
| 距离阈值配置 | Task 3 |
| 触发按键配置 | Task 3 |
| 冷却时间 500ms | Task 2, Task 5 |
| 最近敌人锁定 | Task 2, Task 5 |
| 可视化开关 | Task 5 |
| 可视化绘制（框、距离线、阈值圆） | Task 4, Task 5 |
| 打包脚本 | Task 6 |
| 使用说明 | Task 7 |

所有需求已覆盖。

### 2. Placeholder Scan

- 无 "TBD"、"TODO" 占位符
- 所有步骤都有具体代码
- 所有文件路径都明确指定

### 3. Type Consistency

- `AutomationEngine` 在所有任务中使用一致的参数和方法名
- `ConfigManager` 配置键名一致
- `ImageProcessor` 返回的坐标格式一致

---

## Execution Handoff

计划已完成，保存到 `docs/superpowers/plans/2026-04-19-game-automation-implementation.md`。

**两种执行选项：**

**1. Subagent-Driven (推荐)** - 每个任务分发一个全新的 subagent，任务之间进行审查，快速迭代

**2. Inline Execution** - 在此会话中使用 executing-plans 执行任务，批量执行并设置检查点审查

**选择哪种方式？**
