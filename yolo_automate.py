# yolo_automate.py
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
