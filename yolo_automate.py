# yolo_automate.py
import json
import math
import os
from time import time
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController
import win32gui
import win32ui
import win32con
import numpy as np
from PIL import Image
import cv2 as cv

CONFIG_FILE = "runtime-config.json"


class WindowCapture:
    w = 0
    h = 0
    hwnd = None

    @staticmethod
    def list_available_windows():
        windows = []
        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append((hwnd, title))
            return True
        win32gui.EnumWindows(callback, None)
        return windows

    def __init__(self, window_name):
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise Exception(f'Window not found: {window_name}')
        if win32gui.IsIconic(self.hwnd):
            raise Exception(f'窗口 "{window_name}" 已最小化')
        window_rect = win32gui.GetWindowRect(self.hwnd)
        self.w = window_rect[2] - window_rect[0]
        self.h = window_rect[3] - window_rect[1]
        border_pixels = 8
        titlebar_pixels = 30
        self.w = self.w - (border_pixels * 2)
        self.h = self.h - titlebar_pixels - border_pixels
        self.cropped_x = border_pixels
        self.cropped_y = titlebar_pixels
        if self.w <= 0 or self.h <= 0:
            raise Exception(f'窗口尺寸无效：{self.w} x {self.h}')

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
    windows = WindowCapture.list_available_windows()
    if not windows:
        print("未找到任何可见窗口")
        return None
    print("\n" + "=" * 60)
    print("可用窗口列表:")
    print("=" * 60)
    filtered_windows = [(hwnd, title) for hwnd, title in windows
        if not title.startswith('IME ') and not title.startswith('MSCTFIME ')
        and not title.startswith('Default IME') and not title.startswith(' ') and len(title) > 0]
    if not filtered_windows:
        print("未找到合适的窗口")
        return None
    for i, (hwnd, title) in enumerate(filtered_windows):
        print(f"  [{i + 1}] {title}")
    print("=" * 60)
    while True:
        choice = input(f"请输入窗口编号 (1-{len(filtered_windows)}) 或 'r' 刷新，'q' 退出：").strip()
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


def get_user_settings(saved_config):
    print("\n" + "=" * 60)
    print("配置设置")
    print("=" * 60)
    print(f"\n上次使用的窗口：{saved_config['window_name'] or '未设置'}")
    use_last = input("是否使用上次的窗口配置？(Y/n): ").strip().lower()
    if use_last != 'n' and saved_config['window_name']:
        window_name = saved_config['window_name']
    else:
        show_list = input("是否显示窗口列表供选择？(Y/n): ").strip().lower()
        if show_list != 'n':
            window_name = select_window_from_list()
            if not window_name:
                return None
        else:
            window_name = input("请输入游戏窗口标题：").strip()
        if not window_name:
            print("错误：窗口名称不能为空")
            return None
    print(f"\n上次使用的配置文件：{saved_config['cfg_file']}")
    use_last_cfg = input("是否使用上次的配置文件？(Y/n): ").strip().lower()
    cfg_file = saved_config['cfg_file'] if use_last_cfg != 'n' else (input("cfg 文件路径：").strip() or saved_config['cfg_file'])
    print(f"\n上次使用的权重文件：{saved_config['weights_file']}")
    use_last_weights = input("是否使用上次的权重文件？(Y/n): ").strip().lower()
    weights_file = saved_config['weights_file'] if use_last_weights != 'n' else (input("weights 文件路径：").strip() or saved_config['weights_file'])
    print(f"\n检测频率 FPS (上次：{saved_config['detection_fps']}): ", end='')
    detection_fps = int(input().strip()) if input().strip() else saved_config['detection_fps']
    print(f"\n距离阈值（像素，上次：{saved_config['distance_threshold']}): ", end='')
    distance_threshold = int(input().strip()) if input().strip() else saved_config['distance_threshold']
    print(f"\n触发按键 (上次：{saved_config['trigger_key']}): ", end='')
    trigger_key = input().strip() or saved_config['trigger_key']
    print(f"\n是否开启可视化窗口？(Y/n): ", end='')
    visual_input = input().strip().lower()
    visual_enabled = visual_input != 'n' if visual_input else saved_config['visual_enabled']
    return {'window_name': window_name, 'cfg_file': cfg_file, 'weights_file': weights_file,
        'detection_fps': detection_fps, 'distance_threshold': distance_threshold,
        'trigger_key': trigger_key, 'cooldown_ms': 500, 'visual_enabled': visual_enabled}


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
