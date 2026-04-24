# YOLO OpenCV 游戏自动化工具使用说明

## 功能描述

本工具使用 YOLOv4-tiny 模型检测游戏中的三类目标：
- `1ziji` - 自己的角色（绿色框）
- `2diguihanghui` - 敌对行会的玩家（红色框）
- `3zijihanghui` - 自己行会的玩家（蓝色框）

当检测到敌对行会玩家进入指定距离阈值时，自动触发键盘按键。

**新增功能：后台按键注入**
- 程序自动检测游戏窗口状态
- 窗口在前台：使用标准键盘输入
- 窗口在后台：使用 SendMessage 直接注入按键
- 窗口最小化：程序自动暂停，恢复后继续

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
