# OpenLucky

[English](README.md) | [简体中文](README.zh_Hans.md)

![Version](https://img.shields.io/badge/version-1.4.3--rc.5-4e8cff)
![License](https://img.shields.io/badge/license-Apache%202.0-brightgreen)
![Electron](https://img.shields.io/badge/Electron-41-47848f?logo=electron&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-4fc08d?logo=vuedotjs&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white)

基于 OpenCV 的胶片负片转正处理工具，支持多种胶片预设去色罩。提供命令行工具和桌面应用两种使用方式。

## 桌面应用（Desktop App）

OpenLucky Desktop 是基于 Electron + Vue 3 构建的桌面应用程序，提供直观的图形界面来完成胶片负片的浏览、参数调整和批量处理。

### 照片目录（Photo Directory）

选择包含照片的本地文件夹，应用将加载目录中的所有图片并生成缩略图预览。

- 支持压缩预览模式，加快大量图片的加载速度
- 加载过程中可随时取消
- 支持常见的图片格式（JPG、PNG、TIFF、WebP 及主流相机 RAW 格式）

### 照片编辑（Photo Edit）

核心的负片处理工作区，左侧为缩略图导航栏，右侧为主图显示区和参数控制面板。

#### 参数调节

- **基本参数**：色罩 RGB 通道（Mask-R / Mask-G / Mask-B）、Gamma、对比度
- **乳剂浓度修正**：分通道对比度（Contrast R / G / B），精细调整各通道层次
- **曝光**：曝光补偿调节
- **白平衡**：支持自动白平衡或手动调节色温和色调
- 所有参数支持精确数值输入和步进调节

#### 图像操作

- 主图支持缩放和平移（Ctrl+滚轮、双指手势、键盘快捷键）
- 右键菜单：
  - 复制/粘贴参数
  - 应用预设
  - 拾取色罩颜色
  - 白点区域选择
  - 旋转（顺时针 90°、逆时针 90°、180°）
  - 重置图片
- 直方图实时预览

#### 批量处理

- **应用**：将当前参数应用到当前显示的图片
- **应用全部**：将基础参数批量应用到目录中所有图片
- **保存全部**：将所有已应用参数的图片保存输出

### 多语言与主题

- 支持 14 种语言界面
- 支持深色/浅色主题，可跟随系统自动切换

---

## 命令行工具（CLI）

### 处理单张负片

```powershell
openlucky.exe film -i input.tif -o output.jpg -c config.yaml -p kodak_ultramax_400
```

### 批量处理负片

```powershell
# 输出到 input/output 目录
openlucky.exe filmbatch -i ./input

# 指定输出目录
openlucky.exe filmbatch -i ./input -o ./output

# 使用自定义配置和预设
openlucky.exe filmbatch -i ./input -o ./output -c config.yaml -p kodak_ultramax_400
```

### 格式转换

```powershell
openlucky.exe tiff2jpeg -i input.tif -o output.jpg
```

### 命令行参数

#### openlucky.py film

胶片负片转正处理

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--input` | `-i` | 是 | 输入负片文件路径（支持 .tif, .tiff, .jpg） |
| `--output` | `-o` | 是 | 输出文件保存路径 |
| `--config` | `-c` | 是 | 预设配置文件（YAML）路径 |
| `--preset` | `-p` | 否 | 使用的预设名称（默认：kodak_ultramax_400） |

#### openlucky.py filmbatch

批量处理胶片负片

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--input` | `-i` | 是 | 输入图片目录 |
| `--output` | `-o` | 否 | 输出图片目录（默认：输入目录下的 output 子目录） |
| `--config` | `-c` | 否 | 预设配置文件（YAML）路径（留空则自动查找） |
| `--preset` | `-p` | 否 | 使用的预设名称（默认：kodak_ultramax_400） |

支持的图片格式：`.jpg`、`.jpeg`、`.png`、`.tif`、`.tiff`、`.bmp`

#### openlucky.py tiff2jpeg

TIFF 转 JPEG 格式转换

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--input` | `-i` | 是 | 输入 TIFF 文件路径 |
| `--output` | `-o` | 是 | 输出 JPEG 文件路径 |

---

## 配置文件说明

配置文件 `config.yaml` 使用 YAML 格式，每个预设包含以下参数：

```yaml
presets:
  preset_name:
    mask_r: 215      # 片基红色通道参考值 (0-255)
    mask_g: 145      # 片基绿色通道参考值 (0-255)
    mask_b: 95       # 片基蓝色通道参考值 (0-255)
    contrast: 1.15   # 对比度微调（建议范围：1.0-1.5）
    gamma: 0.45      # Gamma 修正值（建议范围：0.4-2.2）
```

### 参数详解

- **mask_r/mask_g/mask_b**：色罩各通道的参考值，用于除法归一化
- **contrast**：对比度系数，1.0 表示无调整
- **gamma**：Gamma 修正，<1.0 提亮暗部，>1.0 加深暗部

## 内置预设

| 预设名称 | 胶片类型 | 特点 |
|----------|----------|------|
| `kodak_gold_200` | Kodak Gold 200 | 民用卷，色彩温暖 |
| `fuji_c200` | Fuji C200 | 民用卷，色彩偏冷 |
| `kodak_ultramax_400` | Kodak UltraMax 400 | 高感民用卷，色彩鲜艳 |
| `fujifilm_c400` | Fujifilm C400 | 民用高感卷，肤色偏粉 |
| `vision3_50d_5203` | Kodak Vision3 50D | 日光电影卷，颗粒极细 |
| `vision3_250d_5207` | Kodak Vision3 250D | 日光电影卷，全能型 |
| `vision3_200t_5213` | Kodak Vision3 200T | 灯光电影卷 |
| `vision3_500t_5219` | Kodak Vision3 500T | 高感灯光电影卷 |
| `agfa_turia_100s_xx1` | Agfa Turia 100S | 民用卷，对比度高 |

## 自定义预设

在 `config.yaml` 中添加自己的预设：

```yaml
presets:
  my_custom_film:
    mask_r: 200
    mask_g: 140
    mask_b: 100
    contrast: 1.1
    gamma: 0.5
```

使用自定义预设：

```powershell
# 单张处理
openlucky.exe film -i input.tif -o output.jpg -c config.yaml -p my_custom_film

# 批量处理
openlucky.exe filmbatch -i ./input -o ./output -c config.yaml -p my_custom_film
```

## 技术原理

1. **色罩去除** - 根据预设的 mask 值对各通道进行归一化除法
2. **颜色反转** - 将负片图像转换为正片
3. **Gamma 修正** - 调整明暗曲线，使暗部细节更自然
4. **自动色阶** - 根据直方图统计自动调整黑场和白场
5. **对比度调整** - 微调图像对比度

## 许可证

本项目采用 Apache License 2.0 - 详见 LICENSE 文件
