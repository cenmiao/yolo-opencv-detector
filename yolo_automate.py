# yolo_automate.py
import json
import math
import os
from time import time, sleep
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController
import win32gui
import win32ui
import win32con
import win32api
import numpy as np
from PIL import Image
import cv2 as cv

CONFIG_FILE = "runtime-config.json"

# 虚拟键码硬编码映射表（常用键）
VK_CODE_MAP = {
    # 修饰键
    'shift': 0x10, 'ctrl': 0x11, 'alt': 0x12,
    # 功能键
    'space': 0x20, 'enter': 0x0D, 'tab': 0x09, 'esc': 0x1B,
    # 方向键
    'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
    # 功能键 F1-F12
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
}


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
    fps_input = input().strip()
    detection_fps = int(fps_input) if fps_input else saved_config['detection_fps']
    print(f"\n距离阈值（像素，上次：{saved_config['distance_threshold']}): ", end='')
    threshold_input = input().strip()
    distance_threshold = int(threshold_input) if threshold_input else saved_config['distance_threshold']
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


class AutomationEngine:
    """自动化引擎 - 处理距离计算、冷却、按键触发"""

    def __init__(self, distance_threshold, trigger_key, cooldown_ms, hwnd=None):
        self.distance_threshold = distance_threshold
        self.trigger_key = trigger_key
        self.cooldown_ms = cooldown_ms
        self.hwnd = hwnd
        self.last_trigger_time = 0
        self.keyboard = KeyboardController()

    @staticmethod
    def _get_vk_code(key_name):
        """
        获取按键的虚拟键码（VK Code）

        策略：优先使用硬编码映射表，非常用键使用 VkKeyScan 动态查询

        Args:
            key_name: 按键名称（如 'space', 'x', 'enter'）

        Returns:
            int: 虚拟键码
        """
        key_lower = key_name.lower()

        # 优先使用硬编码映射
        if key_lower in VK_CODE_MAP:
            return VK_CODE_MAP[key_lower]

        # 单字符尝试动态查询
        if len(key_name) == 1:
            try:
                vk = win32api.VkKeyScan(key_name)
                # VkKeyScan 返回低字节是 VK 码，高字节是修饰键
                return vk & 0xFF
            except Exception:
                pass

        # 回退：尝试大写字母
        if len(key_name) == 1 and key_name.isalpha():
            try:
                vk = win32api.VkKeyScan(key_name.upper())
                return vk & 0xFF
            except Exception:
                pass

        # 最终回退：返回 'A' 的 VK 码并警告
        print(f"警告：未知按键 '{key_name}'，使用默认 VK 码 (A)")
        return 0x41

    def _send_message_key(self, hwnd, key_name):
        """
        使用 SendMessage 向后台窗口发送按键消息

        Args:
            hwnd: 窗口句柄
            key_name: 按键名称

        Returns:
            bool: 是否发送成功
        """
        if not hwnd:
            print("错误：窗口句柄无效")
            return False

        try:
            vk_code = self._get_vk_code(key_name)

            # 发送 WM_KEYDOWN 和 WM_KEYUP
            # lParam: 重复计数 1 | 扫描码 1 | 扩展键标志 0 | 上下文代码 1 | 先前状态 1
            lparam_down = 0x00000001 | (1 << 16) | (1 << 29) | (1 << 30)
            lparam_up = 0x00000001 | (1 << 16) | (1 << 29) | (1 << 30) | (1 << 31)

            win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, vk_code, lparam_down)
            win32api.SendMessage(hwnd, win32con.WM_KEYUP, vk_code, lparam_up)
            return True

        except Exception as e:
            print(f"SendMessage 失败：{e}")
            return False

    def _ensure_window_visible(self):
        """
        确保游戏窗口可见（未最小化）

        Returns:
            bool: True 如果窗口可用，False 如果需要用户干预
        """
        if not self.hwnd:
            return False

        if not win32gui.IsIconic(self.hwnd):
            # 窗口未最小化，OK
            return True

        # 窗口已最小化，尝试恢复
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            sleep(0.1)  # 给系统时间恢复窗口
            return not win32gui.IsIconic(self.hwnd)
        except Exception as e:
            print(f"恢复窗口失败：{e}")
            return False

    def _pynput_key(self, key_name):
        """使用 pynput 发送按键（前台输入）"""
        try:
            key = getattr(Key, key_name, None)
            if key is None:
                if len(key_name) == 1:
                    key = KeyCode.from_char(key_name)
                else:
                    key_map = {'space': Key.space, 'enter': Key.enter, 'tab': Key.tab,
                               'esc': Key.esc, 'shift': Key.shift, 'ctrl': Key.ctrl, 'alt': Key.alt}
                    key = key_map.get(key_name.lower())
            if key is not None:
                self.keyboard.press(key)
                self.keyboard.release(key)
                return True
        except Exception as e:
            print(f"pynput 按键失败：{e}")
            return False
        return False

    def calculate_distance(self, obj1, obj2):
        """计算两个检测框中心点之间的距离（像素）"""
        center1_x = obj1['x'] + obj1['w'] // 2
        center1_y = obj1['y'] + obj1['h'] // 2
        center2_x = obj2['x'] + obj2['w'] // 2
        center2_y = obj2['y'] + obj2['h'] // 2
        distance = math.sqrt((center2_x - center1_x) ** 2 + (center2_y - center1_y) ** 2)
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
        if distance >= self.distance_threshold:
            return False
        elapsed_ms = current_time_ms - self.last_trigger_time
        if elapsed_ms < self.cooldown_ms:
            return False
        return True

    def trigger_action(self, key_name):
        """
        执行按键动作 - 根据窗口状态自动选择输入方式

        Args:
            key_name: 按键名称

        Returns:
            bool: 是否触发成功
        """
        # 检查窗口是否可用
        if not self._ensure_window_visible():
            print("错误：窗口已最小化且无法恢复，程序暂停")
            print("请恢复窗口后按回车继续，或按 Ctrl+C 退出...")
            try:
                input()
            except KeyboardInterrupt:
                raise
            return False

        try:
            # 判断窗口是否前台
            foreground_hwnd = win32gui.GetForegroundWindow()
            is_foreground = (self.hwnd == foreground_hwnd)

            if is_foreground:
                # 前台：使用 pynput
                return self._pynput_key(key_name)
            else:
                # 后台：使用 SendMessage
                success = self._send_message_key(self.hwnd, key_name)
                # SendMessage 失败时回退到 pynput
                if not success:
                    print("SendMessage 失败，回退到 pynput")
                    return self._pynput_key(key_name)
                return True

        except Exception as e:
            print(f"按键触发失败：{e}")
            return False

    def reset_cooldown(self):
        """重置冷却时间"""
        self.last_trigger_time = time() * 1000

    def get_cooldown_remaining(self, current_time_ms):
        """获取剩余冷却时间（毫秒）"""
        elapsed_ms = current_time_ms - self.last_trigger_time
        return max(0, self.cooldown_ms - elapsed_ms)


class ImageProcessor:
    """图像处理与目标检测类"""

    def __init__(self, img_size, cfg_file, weights_file):
        np.random.seed(42)
        self.classes = {}  # 初始化类别字典
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
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
        self.colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def process_image(self, img):
        """处理图像并返回检测结果"""
        blob = cv.dnn.blobFromImage(img, 1 / 255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward(self.ln)
        outputs = np.vstack(outputs)
        return self.get_coordinates(outputs, 0.5)

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
            coordinates.append({'x': x, 'y': y, 'w': w, 'h': h, 'class': classIDs[i],
                               'class_name': self.classes[classIDs[i]], 'confidence': float(confidences[i])})
        return coordinates

    def draw_identified_objects(self, img, coordinates, distance_threshold=None, automation_engine=None):
        """绘制检测结果，可选显示距离线和阈值圆"""
        player = None
        enemies = []
        for coord in coordinates:
            if coord['class_name'] == '1ziji':
                player = coord
            elif coord['class_name'] == '2diguihanghui':
                enemies.append(coord)
        for coordinate in coordinates:
            x, y, w, h = coordinate['x'], coordinate['y'], coordinate['w'], coordinate['h']
            classID = coordinate['class']
            color = self.colors[classID] if classID < len(self.colors) else (255, 255, 255)
            cv.rectangle(img, (x, y), (x + w, y + h), color, 2)
            cv.putText(img, coordinate['class_name'], (x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        if player and enemies and distance_threshold and automation_engine:
            nearest = automation_engine.find_nearest_enemy(player, enemies)
            if nearest:
                player_cx, player_cy = player['x'] + player['w'] // 2, player['y'] + player['h'] // 2
                enemy_cx, enemy_cy = nearest['x'] + nearest['w'] // 2, nearest['y'] + nearest['h'] // 2
                cv.line(img, (player_cx, player_cy), (enemy_cx, enemy_cy), (0, 255, 255), 2)
                distance = automation_engine.calculate_distance(player, nearest)
                cv.putText(img, f"{distance:.1f}px", ((player_cx + enemy_cx) // 2, (player_cy + enemy_cy) // 2),
                          cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                cv.circle(img, (player_cx, player_cy), int(distance_threshold), (0, 255, 255), 2)


def main():
    """主函数"""
    print("=" * 50)
    print("YOLO OpenCV 游戏自动化工具")
    print("=" * 50)
    print()
    config_manager = ConfigManager()
    print("[加载配置]")
    saved_config = config_manager.load_config()

    try:
        config = get_user_settings(saved_config)
        if config is None:
            print("配置失败，程序退出")
            return
        config_manager.save_config(config)

        print(f"\n正在查找窗口：{config['window_name']}...")
        wincap = WindowCapture(config['window_name'])
        print(f"窗口找到！尺寸：{wincap.w} x {wincap.h}")
        print()

        print("初始化检测模型...")
        improc = ImageProcessor(wincap.get_window_size(), config['cfg_file'], config['weights_file'])
        print("模型加载完成!")
        print()

        automation = AutomationEngine(config['distance_threshold'], config['trigger_key'], config['cooldown_ms'], wincap.hwnd)
        print(f"自动化引擎就绪：阈值={config['distance_threshold']}px, 按键={config['trigger_key']}, 冷却={config['cooldown_ms']}ms")
        print()

        frame_delay = 1.0 / config['detection_fps']
        print("开始自动化检测...")
        print(f"检测频率：{config['detection_fps']} FPS")
        print(f"可视化：{'开启' if config['visual_enabled'] else '关闭'}")
        print("按 'q' 退出，按 'v' 切换可视化")
        print()

        running = True
        visual_enabled = config['visual_enabled']
        error_count = 0
        max_errors = 10  # 最多允许 10 次连续错误

        while running:
            try:
                frame_start = time()
                screenshot = wincap.get_screenshot()
                coordinates = improc.process_image(screenshot)
                error_count = 0  # 成功后重置错误计数

                player = None
                enemies = []
                for coord in coordinates:
                    if coord['class_name'] == '1ziji':
                        player = coord
                    elif coord['class_name'] == '2diguihanghui':
                        enemies.append(coord)

                if player and enemies:
                    nearest = automation.find_nearest_enemy(player, enemies)
                    if nearest:
                        distance = automation.calculate_distance(player, nearest)
                        current_time_ms = time() * 1000
                        if automation.should_trigger(distance, current_time_ms):
                            automation.trigger_action(automation.keyboard, config['trigger_key'])
                            automation.reset_cooldown()
                            print(f"[触发] 距离={distance:.1f}px, 按键={config['trigger_key']}")

                if visual_enabled:
                    try:
                        display_img = screenshot.copy()
                        improc.draw_identified_objects(display_img, coordinates, config['distance_threshold'], automation)
                        status_y = 30
                        cv.putText(display_img, f"FPS: {config['detection_fps']}", (10, status_y), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv.putText(display_img, f"检测到：{len(coordinates)} 个目标", (10, status_y + 30), cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cooldown_remaining = automation.get_cooldown_remaining(time() * 1000)
                        status_text = f"冷却：{cooldown_remaining:.0f}ms" if cooldown_remaining > 0 else "状态：就绪"
                        status_color = (0, 0, 255) if cooldown_remaining > 0 else (0, 255, 0)
                        cv.putText(display_img, status_text, (10, status_y + 60), cv.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                        cv.imshow('YOLO Automation', display_img)
                    except Exception as draw_error:
                        print(f"绘制错误：{draw_error}")
                        # 可视化错误不影响检测，继续运行

                key = cv.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('v'):
                    visual_enabled = not visual_enabled
                    print(f"可视化已{'开启' if visual_enabled else '关闭'}")

                elapsed = time() - frame_start
                if elapsed < frame_delay:
                    sleep(frame_delay - elapsed)

            except Exception as frame_error:
                error_count += 1
                print(f"帧处理错误 ({error_count}/{max_errors}): {frame_error}")
                if error_count >= max_errors:
                    print("连续错误过多，程序退出")
                    break
                sleep(0.1)  # 错误时短暂延迟，避免快速重试

        print('\n检测结束。')

    except Exception as e:
        print(f"\n错误：{e}")
        print("按回车键退出...")
        input()
    finally:
        cv.destroyAllWindows()


if __name__ == "__main__":
    main()
