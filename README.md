# Negative Film Processor

基于 OpenCV 的胶片负片转正处理工具，支持多种胶片预设去色罩。

## 功能特点

- 🔬 **去色罩处理** - 自动移除胶片片基色罩
- 🎨 **多胶片预设** - 内置 Kodak、Fuji、Agfa 等多种胶片预设
- ⚙️ **可自定义配置** - 支持通过 YAML 配置文件创建和编辑自定义预设
- 📊 **高精度处理** - 支持 16-bit TIFF 文件处理，保留更多细节
- 🖼️ **图像增强** - 自动色阶、对比度、Gamma 修正

## 安装

```bash
pip install -r requirements.txt
```

## 快速开始

### 处理负片

```bash
python negative_film.py -i input.tif -o output.jpg -c config.yaml -p kodak_ultramax_400
```

### 转换 TIFF 到 JPEG

如果需要先将 TIFF 文件转换为 JPEG：

```bash
python tiff_to_jpeg.py -i input.tif -o output.jpg
```

## 命令行参数

### negative_film.py

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--input` | `-i` | ✅ | 输入负片文件路径（支持 .tif, .tiff, .jpg） |
| `--output` | `-o` | ✅ | 输出文件保存路径 |
| `--config` | `-c` | ✅ | 预设配置文件（YAML）路径 |
| `--preset` | `-p` | ❌ | 使用的预设名称（默认：kodak_ultramax_400） |

### tiff_to_jpeg.py

| 参数 | 简写 | 必需 | 说明 |
|------|------|------|------|
| `--input` | `-i` | ✅ | 输入 TIFF 文件路径 |
| `--output` | `-o` | ✅ | 输出 JPEG 文件路径 |

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

- **mask_r/mask_g/mask_b**: 色罩各通道的参考值，用于除法归一化
- **contrast**: 对比度系数，1.0 表示无调整
- **gamma**: Gamma 修正，<1.0 提亮暗部，>1.0 加深暗部

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
    mask_r: 200      # 根据实际扫描调整
    mask_g: 140
    mask_b: 100
    contrast: 1.1
    gamma: 0.5
```

使用自定义预设：

```bash
python negative_film.py -i input.tif -o output.jpg -c config.yaml -p my_custom_film
```

## 技术原理

1. **色罩去除** - 根据预设的 mask 值对各通道进行归一化除法
2. **颜色反转** - 将负片图像转换为正片
3. **Gamma 修正** - 调整明暗曲线，使暗部细节更自然
4. **自动色阶** - 根据直方图统计自动调整黑场和白场
5. **对比度调整** - 微调图像对比度

## 许可证

本项目采用 MIT 许可证 - 详见 LICENSE 文件
