"""
游戏自动化工具 - YOLO 检测 + 自动按键触发
支持两种模式：基于自己角色检测 / 基于固定坐标
"""

import json
import math
import os
import sys
import time
import win32gui
import win32ui
import win32con
import win32api
import numpy as np
import cv2 as cv
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController

# 设置 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

CONFIG_FILE = "auto-run.json"


class ConfigManager:
    """配置文件管理器"""

    DEFAULT_CONFIG = {
        "window_name": "",
        "cfg_file": "./yolov4-tiny/yolov4-tiny-custom.cfg",
        "weights_file": "./yolov4-tiny/yolov4-tiny-custom_last.weights",
        "mode": 1,
        "distance_threshold": 200,
        "trigger_key": "space",
        "fixed_position": {"x": 400, "y": 300}
    }

    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = self._load()

    def _load(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 合并默认配置，确保所有字段存在
                    result = self.DEFAULT_CONFIG.copy()
                    result.update(loaded)
                    return result
            except Exception as e:
                print(f"[WARN] 配置文件读取失败: {e}, 使用默认配置")
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()

    def save(self):
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        print(f"[INFO] 配置已保存到 {self.config_file}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value


class WindowSelector:
    """窗口选择器 - 列出所有可见窗口供用户选择"""

    @staticmethod
    def get_visible_windows():
        """获取所有可见窗口列表"""
        windows = []

        def enum_callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and len(title) > 0:
                    windows.append((hwnd, title))
            return True

        win32gui.EnumWindows(enum_callback, None)
        return windows

    @staticmethod
    def select_window(saved_window_name=None):
        """显示窗口列表供用户选择"""
        windows = WindowSelector.get_visible_windows()

        if not windows:
            print("[ERROR] 未找到任何可见窗口")
            return None

        # 过滤掉系统窗口
        filtered = [(hwnd, title) for hwnd, title in windows
                    if not title.startswith('IME ')
                    and not title.startswith('MSCTFIME ')
                    and not title.startswith('Default IME')
                    and not title.startswith('Program Manager')]

        if not filtered:
            filtered = windows

        print("\n" + "=" * 60)
        print("可用窗口列表:")
        print("=" * 60)
        for i, (hwnd, title) in enumerate(filtered, 1):
            print(f"  [{i}] {title}")
        print("=" * 60)

        # 如果有上次保存的窗口，询问是否使用
        if saved_window_name:
            print(f"\n上次使用的窗口: {saved_window_name}")
            use_saved = input("是否使用上次的窗口? (Y/n): ").strip().lower()
            if use_saved != 'n':
                # 验证窗口是否还存在
                for hwnd, title in filtered:
                    if title == saved_window_name or saved_window_name in title:
                        return saved_window_name
                print(f"[WARN] 上次的窗口 '{saved_window_name}' 已不存在")

        while True:
            choice = input(f"请输入窗口编号 (1-{len(filtered)}) 或 'r' 刷新, 'q' 退出: ").strip()
            if choice.lower() == 'q':
                return None
            if choice.lower() == 'r':
                return WindowSelector.select_window(saved_window_name)
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(filtered):
                    return filtered[idx][1]
                print(f"请输入 1-{len(filtered)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")


class WindowCapture:
    """窗口截图类"""

    w = 0
    h = 0
    hwnd = None
    cropped_x = 0
    cropped_y = 0

    def __init__(self, window_name):
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise Exception(f'未找到窗口: {window_name}')

        if win32gui.IsIconic(self.hwnd):
            raise Exception(f'窗口 "{window_name}" 已最小化')

        window_rect = win32gui.GetWindowRect(self.hwnd)
        self.w = window_rect[2] - window_rect[0]
        self.h = window_rect[3] - window_rect[1]

        # 减去边框和标题栏
        border_pixels = 8
        titlebar_pixels = 30
        self.w = self.w - (border_pixels * 2)
        self.h = self.h - titlebar_pixels - border_pixels
        self.cropped_x = border_pixels
        self.cropped_y = titlebar_pixels

        if self.w <= 0 or self.h <= 0:
            raise Exception(f'窗口尺寸无效: {self.w} x {self.h}')

    def get_screenshot(self):
        """截取窗口内容"""
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

        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

        img = img[..., :3]
        img = np.ascontiguousarray(img)
        return img

    def get_window_size(self):
        return (self.w, self.h)


class ImageProcessor:
    """YOLO 图像处理器"""

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

        cfg_path = cfg_file
        if not os.path.exists(cfg_path):
            cfg_path = os.path.join(base_path, cfg_file.lstrip('./'))

        weights_path = weights_file
        if not os.path.exists(weights_path):
            weights_path = os.path.join(base_path, weights_file.lstrip('./'))

        print(f"[INFO] 加载配置: {cfg_path}")
        print(f"[INFO] 加载权重: {weights_path}")

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

        print(f"[INFO] 加载类别: {names_path}")
        with open(names_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f.readlines()):
                self.classes[i] = line.strip()

        # 检测框颜色: ziji=绿, dangeroususer=红, normaluser=黄
        self.colors = [
            (0, 255, 0),    # ziji - 绿色
            (0, 0, 255),    # dangeroususer - 红色
            (255, 255, 0),  # normaluser - 黄色
        ]

    def process_image(self, img, confidence=0.5):
        """处理图像返回检测结果"""
        blob = cv.dnn.blobFromImage(img, 1/255.0, (416, 416), swapRB=True, crop=False)
        self.net.setInput(blob)
        outputs = self.net.forward(self.ln)
        outputs = np.vstack(outputs)
        return self._get_coordinates(outputs, confidence)

    def _get_coordinates(self, outputs, conf):
        """解析检测结果"""
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

        indices = cv.dnn.NMSBoxes(boxes, confidences, conf, max(0.1, conf - 0.1))
        if len(indices) == 0:
            return []

        coordinates = []
        for i in indices.flatten():
            x, y, w, h = boxes[i][0], boxes[i][1], boxes[i][2], boxes[i][3]
            coordinates.append({
                'x': x, 'y': y, 'w': w, 'h': h,
                'class': classIDs[i],
                'class_name': self.classes.get(classIDs[i], 'unknown'),
                'confidence': float(confidences[i])
            })
        return coordinates


# 虚拟键码映射
VK_CODE_MAP = {
    'space': 0x20, 'enter': 0x0D, 'tab': 0x09, 'esc': 0x1B,
    'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'shift': 0x10, 'ctrl': 0x11, 'alt': 0x12,
}


class AutomationEngine:
    """自动化引擎 - 处理距离计算和按键触发"""

    def __init__(self, distance_threshold, trigger_key, hwnd=None):
        self.distance_threshold = distance_threshold
        self.trigger_key = trigger_key
        self.hwnd = hwnd
        self.keyboard = KeyboardController()

    def calculate_distance(self, obj1, obj2):
        """计算两个检测框中心点距离"""
        cx1 = obj1['x'] + obj1['w'] // 2
        cy1 = obj1['y'] + obj1['h'] // 2
        cx2 = obj2['x'] + obj2['w'] // 2
        cy2 = obj2['y'] + obj2['h'] // 2
        return math.sqrt((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2)

    def find_nearest_enemy(self, player_pos, enemies):
        """找最近的敌人"""
        if not enemies:
            return None, None
        nearest = None
        min_dist = float('inf')
        for enemy in enemies:
            dist = self.calculate_distance(player_pos, enemy)
            if dist < min_dist:
                min_dist = dist
                nearest = enemy
        return nearest, min_dist

    def trigger_action(self):
        """触发按键动作"""
        try:
            # 判断窗口是否前台
            foreground = win32gui.GetForegroundWindow()
            is_foreground = (self.hwnd == foreground)

            if is_foreground:
                self._pynput_key()
            else:
                self._send_message_key()

            return True
        except Exception as e:
            print(f"[WARN] 按键触发失败: {e}")
            return False

    def _pynput_key(self):
        """使用 pynput 发送按键"""
        key_name = self.trigger_key.lower()
        key = getattr(Key, key_name, None)
        if key is None:
            if len(self.trigger_key) == 1:
                key = KeyCode.from_char(self.trigger_key)
            else:
                key_map = {
                    'space': Key.space, 'enter': Key.enter,
                    'tab': Key.tab, 'esc': Key.esc
                }
                key = key_map.get(key_name)
        if key:
            self.keyboard.press(key)
            self.keyboard.release(key)

    def _send_message_key(self):
        """使用 SendMessage 后台发送按键"""
        vk_code = self._get_vk_code(self.trigger_key)
        lparam_down = 0x00000001 | (1 << 16) | (1 << 29) | (1 << 30)
        lparam_up = lparam_down | (1 << 31)
        win32api.SendMessage(self.hwnd, win32con.WM_KEYDOWN, vk_code, lparam_down)
        win32api.SendMessage(self.hwnd, win32con.WM_KEYUP, vk_code, lparam_up)

    def _get_vk_code(self, key_name):
        """获取虚拟键码"""
        key_lower = key_name.lower()
        if key_lower in VK_CODE_MAP:
            return VK_CODE_MAP[key_lower]
        if len(key_name) == 1:
            try:
                vk = win32api.VkKeyScan(key_name)
                return vk & 0xFF
            except Exception:
                pass
        return 0x41  # 默认回退到 'A'

    def mode1_process(self, coordinates):
        """模式一处理: 基于 ziji 检测"""
        player = None
        enemies = []

        for coord in coordinates:
            class_name = coord['class_name']
            if class_name == 'ziji':
                player = coord
            elif class_name == 'dangeroususer':
                enemies.append(coord)

        if not player or not enemies:
            return None, None, None

        nearest, distance = self.find_nearest_enemy(player, enemies)
        return player, nearest, distance

    def mode2_process(self, coordinates, fixed_pos):
        """模式二处理: 基于固定坐标"""
        enemies = []
        for coord in coordinates:
            if coord['class_name'] == 'dangeroususer':
                enemies.append(coord)

        if not enemies:
            return None, None, None

        # 固定坐标作为玩家位置
        player_pos = {
            'x': fixed_pos['x'],
            'y': fixed_pos['y'],
            'w': 0,
            'h': 0
        }
        nearest, distance = self.find_nearest_enemy(player_pos, enemies)
        return player_pos, nearest, distance


def draw_detection(img, coordinates, player, nearest_enemy, distance,
                   threshold, mode, fixed_pos=None):
    """绘制检测结果和状态信息"""

    # 绘制所有检测框
    for coord in coordinates:
        x, y, w, h = coord['x'], coord['y'], coord['w'], coord['h']
        class_name = coord['class_name']

        # 根据类别选择颜色
        if class_name == 'ziji':
            color = (0, 255, 0)  # 绿色
        elif class_name == 'dangeroususer':
            color = (0, 0, 255)  # 红色
        elif class_name == 'normaluser':
            color = (255, 255, 0)  # 黄色
        else:
            color = (255, 255, 255)  # 白色

        cv.rectangle(img, (x, y), (x + w, y + h), color, 2)
        cv.putText(img, class_name, (x, y - 10),
                   cv.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # 绘制玩家位置和坐标文本
    if player:
        px = player['x'] + player['w'] // 2
        py = player['y'] + player['h'] // 2

        # 绘制玩家中心点
        cv.circle(img, (px, py), 5, (0, 255, 0), -1)

        # 显示玩家坐标（核心需求）
        coord_text = f"Player: ({px}, {py})"
        cv.putText(img, coord_text, (10, 30),
                   cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # 绘制阈值圆
        cv.circle(img, (px, py), int(threshold), (0, 255, 255), 2)

    # 模式二绘制固定坐标点
    if mode == 2 and fixed_pos:
        fx, fy = fixed_pos['x'], fixed_pos['y']
        cv.circle(img, (fx, fy), 5, (255, 0, 255), -1)
        cv.putText(img, f"Fixed: ({fx}, {fy})", (10, 60),
                   cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

    # 绘制连线到最近敌人
    if nearest_enemy and player:
        px = player['x'] + player['w'] // 2
        py = player['y'] + player['h'] // 2
        ex = nearest_enemy['x'] + nearest_enemy['w'] // 2
        ey = nearest_enemy['y'] + nearest_enemy['h'] // 2

        cv.line(img, (px, py), (ex, ey), (0, 255, 255), 2)

        # 显示距离
        mid_x = (px + ex) // 2
        mid_y = (py + ey) // 2
        cv.putText(img, f"{distance:.1f}px", (mid_x, mid_y),
                   cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    # 显示状态信息
    status_y = 90 if mode == 2 else 60
    mode_text = f"Mode: {mode}"
    cv.putText(img, mode_text, (10, status_y),
               cv.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv.imshow('Game Automation', img)


def get_user_config(config_mgr):
    """获取用户配置信息"""
    saved = config_mgr.config

    print("\n" + "=" * 60)
    print("配置设置")
    print("=" * 60)

    # 1. 窗口选择
    window_name = WindowSelector.select_window(saved.get('window_name'))
    if not window_name:
        print("[INFO] 用户取消，程序退出")
        return None
    config_mgr.set('window_name', window_name)

    # 2. 配置文件
    print(f"\n上次 cfg 文件: {saved.get('cfg_file')}")
    use_saved = input("使用上次的 cfg 文件? (Y/n): ").strip().lower()
    if use_saved != 'n':
        cfg_file = saved.get('cfg_file')
    else:
        cfg_file = input("cfg 文件路径: ").strip() or saved.get('cfg_file')
    config_mgr.set('cfg_file', cfg_file)

    # 3. 权重文件
    print(f"\n上次 weights 文件: {saved.get('weights_file')}")
    use_saved = input("使用上次的 weights 文件? (Y/n): ").strip().lower()
    if use_saved != 'n':
        weights_file = saved.get('weights_file')
    else:
        weights_file = input("weights 文件路径: ").strip() or saved.get('weights_file')
    config_mgr.set('weights_file', weights_file)

    # 4. 自动化模式
    print("\n自动化模式:")
    print("  [1] 模式一: 基于 ziji 检测 (自己角色)")
    print("  [2] 模式二: 基于固定坐标 (模型无法识别自己时)")
    mode_input = input(f"选择模式 (1/2, 上次: {saved.get('mode')}): ").strip()
    mode = int(mode_input) if mode_input in ['1', '2'] else saved.get('mode', 1)
    config_mgr.set('mode', mode)

    # 5. 距离阈值
    print(f"\n距离阈值 (像素, 上次: {saved.get('distance_threshold')}): ", end='')
    threshold_input = input().strip()
    threshold = int(threshold_input) if threshold_input else saved.get('distance_threshold', 200)
    config_mgr.set('distance_threshold', threshold)

    # 6. 触发按键
    print(f"\n触发按键 (上次: {saved.get('trigger_key')}): ", end='')
    key_input = input().strip()
    trigger_key = key_input or saved.get('trigger_key', 'space')
    config_mgr.set('trigger_key', trigger_key)

    # 7. 模式二额外配置固定坐标
    if mode == 2:
        fixed = saved.get('fixed_position', {'x': 400, 'y': 300})
        print(f"\n固定坐标 X (上次: {fixed['x']}): ", end='')
        x_input = input().strip()
        fixed['x'] = int(x_input) if x_input else fixed['x']
        print(f"固定坐标 Y (上次: {fixed['y']}): ", end='')
        y_input = input().strip()
        fixed['y'] = int(y_input) if y_input else fixed['y']
        config_mgr.set('fixed_position', fixed)

    # 保存配置
    config_mgr.save()

    return config_mgr.config


def main():
    """主程序入口"""
    print("=" * 60)
    print("游戏自动化工具 - YOLO 检测 + 自动按键")
    print("=" * 60)

    # 加载配置
    config_mgr = ConfigManager()
    config = get_user_config(config_mgr)
    if config is None:
        return

    # 初始化窗口截图
    try:
        print(f"\n[INFO] 正在查找窗口: {config['window_name']}")
        wincap = WindowCapture(config['window_name'])
        print(f"[INFO] 窗口找到! 尺寸: {wincap.w} x {wincap.h}")
    except Exception as e:
        print(f"[ERROR] 窗口初始化失败: {e}")
        return

    # 初始化 YOLO 模型
    try:
        improc = ImageProcessor(
            wincap.get_window_size(),
            config['cfg_file'],
            config['weights_file']
        )
        print("[INFO] YOLO 模型加载完成")
    except Exception as e:
        print(f"[ERROR] 模型加载失败: {e}")
        return

    # 初始化自动化引擎
    automation = AutomationEngine(
        config['distance_threshold'],
        config['trigger_key'],
        wincap.hwnd
    )

    mode = config['mode']
    threshold = config['distance_threshold']
    fixed_pos = config.get('fixed_position', {'x': 400, 'y': 300})

    print(f"\n[INFO] 模式: {mode}, 阈值: {threshold}px, 按键: {config['trigger_key']}")
    print("[INFO] 按 'q' 退出, 按 'v' 切换可视化")
    print("=" * 60)

    visual_enabled = True

    # 主循环
    while True:
        try:
            screenshot = wincap.get_screenshot()
            coordinates = improc.process_image(screenshot)

            # 根据模式处理
            if mode == 1:
                player, nearest, distance = automation.mode1_process(coordinates)
            else:
                player, nearest, distance = automation.mode2_process(coordinates, fixed_pos)

            # 检测到敌人且距离小于阈值
            if nearest and distance < threshold:
                automation.trigger_action()
                print(f"[TRIGGER] 模式{mode}: 距离={distance:.1f}px, 按键={config['trigger_key']}")

            # 打印玩家坐标（核心需求）
            if player:
                px = player['x'] + player['w'] // 2
                py = player['y'] + player['h'] // 2
                print(f"[POS] Player坐标: ({px}, {py})")

            # 可视化绘制
            if visual_enabled:
                draw_detection(
                    screenshot, coordinates, player, nearest,
                    distance, threshold, mode, fixed_pos
                )

            # 检查按键
            key = cv.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n[INFO] 用户退出")
                break
            elif key == ord('v'):
                visual_enabled = not visual_enabled
                if not visual_enabled:
                    cv.destroyWindow('Game Automation')
                print(f"[INFO] 可视化: {'开启' if visual_enabled else '关闭'}")

        except Exception as e:
            print(f"[WARN] 检测帧错误: {e}")
            continue

    cv.destroyAllWindows()
    print("[INFO] 程序结束")


if __name__ == '__main__':
    main()