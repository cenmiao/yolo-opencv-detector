# 后台按键注入功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现自动感知游戏窗口状态并选择合适的按键输入方式（前台 pynput / 后台 SendMessage）

**Architecture:** 
- 在 `AutomationEngine.__init__` 中添加 `hwnd` 参数
- 新增 `_get_vk_code` 静态方法处理按键映射（硬编码 + VkKeyScan 回退）
- 新增 `_send_message_key` 方法实现后台按键注入
- 重构 `trigger_action` 方法，增加窗口状态判断和分派逻辑

**Tech Stack:** pywin32 (win32gui, win32api, win32con), pynput

---

### Task 1: 添加 VK 码映射表和导入 win32api

**Files:**
- Modify: `yolo_automate.py:1-12`

- [ ] **Step 1: 添加 win32api 导入**

在文件顶部的 import 区域添加 `win32api`：

```python
import win32gui
import win32ui
import win32con
import win32api  # 新增
```

- [ ] **Step 2: 定义 VK 码硬编码映射表**

在 `CONFIG_FILE` 定义之后添加常量：

```python
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
```

- [ ] **Step 3: 提交**

```bash
git add yolo_automate.py
git commit -m "refactor: add VK code map for SendMessage key injection"
```

---

### Task 2: 实现 VK 码获取辅助方法

**Files:**
- Modify: `yolo_automate.py:204-212` (AutomationEngine 类内)

- [ ] **Step 1: 添加静态方法 `_get_vk_code`**

在 `AutomationEngine` 类中添加（放在 `__init__` 之后）：

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add yolo_automate.py
git commit -m "feat: add _get_vk_code helper with hardcoded + VkKeyScan fallback"
```

---

### Task 3: 实现 SendMessage 后台按键注入方法

**Files:**
- Modify: `yolo_automate.py:204-273` (AutomationEngine 类内)

- [ ] **Step 1: 添加 `_send_message_key` 方法**

在 `_get_vk_code` 方法后添加：

```python
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
            # lParam: 0x00000001 | (1 << 16) | (0 << 29) | (1 << 30) | (1 << 31)
            # = 重复计数 1 | 扫描码 1 | 扩展键标志 0 | 上下文代码 1 | 先前状态 1
            lparam_down = 0x00000001 | (1 << 16) | (1 << 29) | (1 << 30)
            lparam_up = 0x00000001 | (1 << 16) | (1 << 29) | (1 << 30) | (1 << 31)
            
            win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, vk_code, lparam_down)
            win32api.SendMessage(hwnd, win32con.WM_KEYUP, vk_code, lparam_up)
            return True
            
        except Exception as e:
            print(f"SendMessage 失败：{e}")
            return False
```

- [ ] **Step 2: 提交**

```bash
git add yolo_automate.py
git commit -m "feat: add _send_message_key for background key injection"
```

---

### Task 4: 重构 AutomationEngine 构造函数添加 hwnd

**Files:**
- Modify: `yolo_automate.py:204-212`
- Modify: `yolo_automate.py:399` (调用处)

- [ ] **Step 1: 修改 `__init__` 签名**

```python
    def __init__(self, distance_threshold, trigger_key, cooldown_ms, hwnd=None):
        self.distance_threshold = distance_threshold
        self.trigger_key = trigger_key
        self.cooldown_ms = cooldown_ms
        self.hwnd = hwnd  # 新增：游戏窗口句柄
        self.last_trigger_time = 0
        self.keyboard = KeyboardController()
```

- [ ] **Step 2: 修改 main() 中的调用**

在 `main()` 函数中找到 `AutomationEngine` 实例化位置，修改为：

```python
# 在创建 wincap 后，hwnd 已经可用
automation = AutomationEngine(
    config['distance_threshold'], 
    config['trigger_key'], 
    config['cooldown_ms'],
    wincap.hwnd  # 传递窗口句柄
)
```

- [ ] **Step 3: 提交**

```bash
git add yolo_automate.py
git commit -m "refactor: add hwnd parameter to AutomationEngine"
```

---

### Task 5: 实现窗口状态检测和 trigger_action 重构

**Files:**
- Modify: `yolo_automate.py:245-263` (trigger_action 方法)

- [ ] **Step 1: 添加窗口恢复辅助方法**

在 `_send_message_key` 后添加：

```python
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
```

- [ ] **Step 2: 重构 `trigger_action` 方法**

```python
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
```

- [ ] **Step 3: 重命名原有的 trigger_action 为 _pynput_key**

```python
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
```

- [ ] **Step 4: 提交**

```bash
git add yolo_automate.py
git commit -m "feat: auto-detect window state and select input method"
```

---

### Task 6: 修改 main() 中的 trigger_action 调用

**Files:**
- Modify: `yolo_automate.py:435-438`

- [ ] **Step 1: 简化 trigger_action 调用**

原代码：
```python
if automation.should_trigger(distance, current_time_ms):
    automation.trigger_action(automation.keyboard, config['trigger_key'])
    automation.reset_cooldown()
    print(f"[触发] 距离={distance:.1f}px, 按键={config['trigger_key']}")
```

新代码（移除 `automation.keyboard` 参数）：
```python
if automation.should_trigger(distance, current_time_ms):
    automation.trigger_action(config['trigger_key'])
    automation.reset_cooldown()
    print(f"[触发] 距离={distance:.1f}px, 按键={config['trigger_key']}")
```

- [ ] **Step 2: 提交**

```bash
git add yolo_automate.py
git commit -m "refactor: update trigger_action call signature"
```

---

### Task 7: 添加窗口最小化暂停/恢复机制

**Files:**
- Modify: `yolo_automate.py:410-473` (main 循环)

- [ ] **Step 1: 添加暂停标志**

在 `running = True` 后添加：
```python
paused = False  # 窗口最小化暂停标志
```

- [ ] **Step 2: 在 `_ensure_window_visible` 失败时设置暂停**

修改 `_ensure_window_visible` 返回 False 后的逻辑，在 `trigger_action` 中：
```python
# 检查窗口是否可用
if not self._ensure_window_visible():
    print("错误：窗口已最小化且无法恢复，程序暂停")
    return 'paused'  # 返回特殊状态而不是 False

# ... 其余逻辑
```

- [ ] **Step 3: 在 main 循环中处理暂停状态**

修改检测循环中的触发逻辑：
```python
if player and enemies:
    nearest = automation.find_nearest_enemy(player, enemies)
    if nearest:
        distance = automation.calculate_distance(player, nearest)
        current_time_ms = time() * 1000
        if automation.should_trigger(distance, current_time_ms):
            result = automation.trigger_action(config['trigger_key'])
            if result == 'paused':
                paused = True
                print("程序已暂停，等待用户恢复窗口...")
                while paused:
                    # 检查用户是否按了回车
                    key = cv.waitKey(0) & 0xFF
                    if key == ord('q'):
                        running = False
                        break
                    # 检查窗口是否恢复
                    try:
                        if not win32gui.IsIconic(wincap.hwnd):
                            print("窗口已恢复，继续运行")
                            paused = False
                    except:
                        pass
            else:
                automation.reset_cooldown()
                print(f"[触发] 距离={distance:.1f}px, 按键={config['trigger_key']}")
```

- [ ] **Step 4: 提交**

```bash
git add yolo_automate.py
git commit -m "feat: add pause/resume on window minimize"
```

---

### Task 8: 测试验证

**Files:**
- Test: 手动测试

- [ ] **Step 1: 前台窗口测试**
  - 运行 `python yolo_automate.py`
  - 游戏窗口保持前台
  - 验证：检测到敌人时按键正常触发

- [ ] **Step 2: 后台窗口测试**
  - 运行程序后切换到其他窗口（如浏览器）
  - 验证：检测到敌人时按键仍然触发（通过 SendMessage）

- [ ] **Step 3: 最小化恢复测试**
  - 最小化游戏窗口
  - 验证：程序暂停并提示
  - 恢复窗口后验证：程序自动继续

- [ ] **Step 4: 按键映射测试**
  - 测试常用键：space, x, z, enter
  - 验证：所有按键都能正确触发

---

### Task 9: 重新打包 EXE

**Files:**
- Modify: `build_automate.bat`
- Create: `dist/yolo_automate.exe`

- [ ] **Step 1: 运行打包脚本**

```bash
./build_automate.bat
```

- [ ] **Step 2: 验证输出**

确认以下文件存在：
- `dist/yolo_automate.exe`
- `dist/yolov4-tiny-custom.cfg`
- `dist/yolov4-tiny-custom_last.weights`
- `dist/yolov4-tiny/obj.names`

- [ ] **Step 3: 提交**

```bash
git add dist/
git commit -m "build: rebuild yolo_automate.exe with background input support"
```

---

### Task 10: 更新文档

**Files:**
- Modify: `dist/AUTOMATE_README.md`

- [ ] **Step 1: 更新功能描述**

在功能描述中添加：
```markdown
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
```

- [ ] **Step 2: 提交**

```bash
git add dist/AUTOMATE_README.md
git commit -m "docs: update AUTOMATE_README with background input feature"
```

---

## 自检清单

- [ ] **Spec 覆盖检查**：
  - [x] 窗口状态检测 → Task 5
  - [x] 前台使用 pynput → Task 5
  - [x] 后台使用 SendMessage → Task 3, 5
  - [x] 最小化尝试恢复 → Task 5, 7
  - [x] VK 码映射（硬编码 + VkKeyScan）→ Task 1, 2
  - [x] 错误处理 → 各 Task 中 try-except

- [ ] **无占位符检查**：无 TBD/TODO

- [ ] **类型一致性检查**：
  - `trigger_action` 签名已统一为 `(self, key_name)`
  - `hwnd` 在 `__init__` 中赋值并在后续方法中使用
  - 返回值：`_pynput_key` / `_send_message_key` 均返回 `bool`

- [ ] **测试覆盖**：Task 8 包含所有测试要点
