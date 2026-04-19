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
