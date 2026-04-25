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

# 设置控制台 UTF-8 输出，避免 Windows GBK 编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 配置文件名
CONFIG_FILE = "detector_config.json"
ERROR_LOG_FILE = "error.log"


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

        nms_threshold = max(0.1, conf - 0.1)
        indices = cv.dnn.NMSBoxes(boxes, confidences, conf, nms_threshold)

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


def log_error(error_msg):
    """将错误写入日志文件"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {error_msg}\n"

    with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

    print(f"[ERROR] {error_msg}, 继续检测...")


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
