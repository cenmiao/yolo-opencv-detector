# Google Colab 训练 YOLOv4-tiny 详细指南

> **前提条件**：已完成数据标注，拥有标注好的图片和 .txt 文件

---

## 一、准备工作

### 1.1 准备文件清单

在上传到 Google Drive 之前，确保你有以下文件：

```
yolov4-tiny/
├── obj.data                    # 数据配置（项目已有）
├── obj.names                   # 类别名称（项目已有）
├── yolov4-tiny-custom.cfg      # 网络配置（项目已有）
├── yolov4-tiny.conv.29         # 预训练权重（项目已有）
├── process.py                  # 数据处理脚本（项目已有）
└── images/                     # 标注好的图片和 .txt 文件
    ├── img_1.jpg
    ├── img_1.txt
    ├── img_2.jpg
    ├── img_2.txt
    └── ...
```

### 1.2 打包上传文件

将以下文件打包成 `obj.zip`：
- `images/` 目录（包含所有图片和 .txt 标注文件）

将以下文件单独放到 Google Drive 的 `yolov4-tiny/` 文件夹：
- `obj.data`
- `obj.names`
- `yolov4-tiny-custom.cfg`
- `yolov4-tiny.conv.29`
- `process.py`
- `obj.zip`

---

## 二、Google Drive 文件结构

在 Google Drive 中创建以下结构：

```
My Drive/
└── yolov4-tiny/
    ├── obj.data
    ├── obj.names
    ├── yolov4-tiny-custom.cfg
    ├── yolov4-tiny.conv.29
    ├── process.py
    └── obj.zip (包含 images/ 目录和标注文件)
```

### obj.data 文件内容示例：
```
classes = 3
train = data/train.txt
valid = data/test.txt
names = data/obj.names
backup = backup/
```

### obj.names 文件内容示例：
```
assaulter
freezer
heater
```
（根据你的实际类别修改）

---

## 三、Google Colab 训练步骤

### 步骤 1：打开 Google Colab

1. 访问 https://colab.research.google.com/
2. 点击 "上传" 或直接打开新的 notebook

### 步骤 2：创建训练 Notebook

新建一个 notebook，依次运行以下单元格：

#### 单元格 1：克隆 Darknet 框架
```python
!git clone https://github.com/AlexeyAB/darknet
```

#### 单元格 2：挂载 Google Drive
```python
%cd darknet
from google.colab import drive
drive.mount('/content/gdrive')
!ln -s /content/gdrive/My\ Drive/ /mydrive
```
运行后会弹出授权窗口，按提示授权并复制授权码。

#### 单元格 3：验证 Drive 文件
```python
!ls /mydrive/yolov4-tiny
```
确认能看到你上传的文件。

#### 单元格 4：配置 Darknet 编译选项
```python
%cd /content/darknet/
!sed -i 's/OPENCV=0/OPENCV=1/' Makefile
!sed -i 's/GPU=0/GPU=1/' Makefile
!sed -i 's/CUDNN=0/CUDNN=1/' Makefile
!sed -i 's/CUDNN_HALF=0/CUDNN_HALF=1/' Makefile
!sed -i 's/LIBSO=0/LIBSO=1/' Makefile
```

#### 单元格 5：编译 Darknet
```python
!make
```
编译需要约 5-10 分钟。

#### 单元格 6：清理默认数据目录
```python
%cd data/
!find -maxdepth 1 -type f -exec rm -rf {} \;
%cd ..
%rm -rf cfg/
%mkdir cfg
```

#### 单元格 7：复制训练文件
```python
!cp /mydrive/yolov4-tiny/obj.zip ../
!unzip ../obj.zip -d data/

!cp /mydrive/yolov4-tiny/yolov4-tiny-custom.cfg ./cfg/
!cp /mydrive/yolov4-tiny/obj.names ./data/
!cp /mydrive/yolov4-tiny/obj.data ./data/
!cp /mydrive/yolov4-tiny/process.py ./
!cp /mydrive/yolov4-tiny/yolov4-tiny.conv.29 ./
```

#### 单元格 8：处理数据（生成 train.txt 和 test.txt）
```python
!python process.py
```

#### 单元格 9：验证文件
```python
!ls data/
```
应该看到：`obj.data`, `obj.names`, `train.txt`, `test.txt`, `images/` 等

#### 单元格 10：开始训练
```python
!./darknet detector train data/obj.data cfg/yolov4-tiny-custom.cfg yolov4-tiny.conv.29 -dont_show
```

---

## 四、训练过程

训练开始后，你会看到类似输出：
```
Loaded: 0.000000
Region
Next Region
...
```

训练时间取决于：
- 图片数量（100-500 张约需 1-2 小时）
- GPU 性能（Colab 通常提供 Tesla T4 或 K80）

### 训练参数说明

在 `yolov4-tiny-custom.cfg` 中可以调整：
- `max_batches`：最大训练批次（建议设置为 `类别数 × 2000`，至少 2000）
- `steps`：学习率调整点（建议 `max_batches` 的 80% 和 90%）
- `batch`：每批次图片数量（Colab 建议 64 或 128）
- `subdivisions`：批次分割数（Colab 建议 16 或 32）

---

## 五、训练完成

### 步骤 1：等待训练完成

训练完成后会看到：
```
avg IoU=xx.xx
```

### 步骤 2：找到权重文件

训练好的权重文件位于：
```
/content/darknet/yolov4-tiny/yolov4-tiny-custom_last.weights
```

### 步骤 3：下载到本地

**方法 A：通过 Google Drive**
```python
!cp /content/darknet/yolov4-tiny/yolov4-tiny-custom_last.weights /mydrive/yolov4-tiny/
```
然后从 Google Drive 下载到本地电脑。

**方法 B：直接下载**
```python
from google.colab import files
files.download('/content/darknet/yolov4-tiny/yolov4-tiny-custom_last.weights')
```

---

## 六、使用训练好的权重

将下载的 `yolov4-tiny-custom_last.weights` 文件放到：
```
dist/yolov4-tiny-custom_last.weights
```

然后运行：
```
yolo_automate.exe
```

---

## 七、常见问题

### Q1: 训练时出现 "CUDA out of memory"
**解决方案**：在 `yolov4-tiny-custom.cfg` 中增大 `subdivisions` 值（如从 16 改为 32 或 64）

### Q2: 训练Loss不下降
**解决方案**：
- 检查标注文件是否正确
- 增加训练批次（max_batches）
- 调整学习率（scale 参数）

### Q3: 检测效果不好
**解决方案**：
- 增加训练图片数量
- 确保标注准确
- 调整 `max_batches` 和 `steps` 参数

### Q4: Colab 断开连接
**解决方案**：
- Colab 有使用时限（通常 12 小时）
- 可以在浏览器按 F12 运行以下代码保持连接：
```javascript
function ConnectButton(){console.log("Connect pressed");document.querySelector("#top-toolbar > colab-toolbar-runtime#top-toolbar > colab-toolbar-runtime#top-toolbar > colab-toolbar-runtime").shadowRoot.querySelector("#connect-button").click()}setInterval(ConnectButton,60000);
```

---

## 八、快速训练脚本（完整 Notebook）

将以下所有内容复制到一个新的 Colab Notebook 中，然后依次运行：

```python
# ========== 1. 克隆 Darknet ==========
!git clone https://github.com/AlexeyAB/darknet

# ========== 2. 挂载 Google Drive ==========
%cd darknet
from google.colab import drive
drive.mount('/content/gdrive')
!ln -s /content/gdrive/My\ Drive/ /mydrive

# ========== 3. 配置编译选项 ==========
%cd /content/darknet/
!sed -i 's/OPENCV=0/OPENCV=1/' Makefile
!sed -i 's/GPU=0/GPU=1/' Makefile
!sed -i 's/CUDNN=0/CUDNN=1/' Makefile
!sed -i 's/CUDNN_HALF=0/CUDNN_HALF=1/' Makefile

# ========== 4. 编译 Darknet ==========
!make

# ========== 5. 复制训练文件 ==========
%cd /content/darknet/
!cp /mydrive/yolov4-tiny/obj.zip ../
!unzip ../obj.zip -d data/
!cp /mydrive/yolov4-tiny/yolov4-tiny-custom.cfg ./cfg/
!cp /mydrive/yolov4-tiny/obj.names ./data/
!cp /mydrive/yolov4-tiny/obj.data ./data/
!cp /mydrive/yolov4-tiny/process.py ./
!cp /mydrive/yolov4-tiny/yolov4-tiny.conv.29 ./

# ========== 6. 处理数据 ==========
!python process.py

# ========== 7. 开始训练 ==========
!./darknet detector train data/obj.data cfg/yolov4-tiny-custom.cfg yolov4-tiny.conv.29 -dont_show

# ========== 8. 下载权重文件 ==========
from google.colab import files
files.download('/content/darknet/yolov4-tiny/yolov4-tiny-custom_last.weights')
```

---

## 九、训练完成后

1. 将下载的权重文件放到 `dist/` 目录
2. 运行 `yolo_automate.exe`
3. 输入游戏窗口名称
4. 开始自动化！
