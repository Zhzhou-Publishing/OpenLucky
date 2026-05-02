# OpenLucky

[English](README.md) | [简体中文](README.zh_Hans.md)

![Version](https://img.shields.io/badge/version-1.4.3--rc.5-4e8cff)
![License](https://img.shields.io/badge/license-Apache%202.0-brightgreen)
![Electron](https://img.shields.io/badge/Electron-41-47848f?logo=electron&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3.5-4fc08d?logo=vuedotjs&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white)

An OpenCV-based film negative conversion tool that removes color masks using built-in film presets. Available as both a command-line tool and a desktop application.

## Desktop App

OpenLucky Desktop is an Electron + Vue 3 application that provides an intuitive graphical interface for browsing, adjusting, and batch-processing film negatives.

### Photo Directory

Select a local folder containing your photos. The app loads all images in the directory and generates thumbnail previews.

- Compress preview mode for faster loading of large photo sets
- Cancel loading at any time
- Supports common image formats (JPG, PNG, TIFF, WebP, and major camera RAW formats)

### Photo Edit

The core negative processing workspace, with a thumbnail strip on the left and a main image viewer plus parameter controls on the right.

#### Parameter Controls

- **Basic Parameters**: Mask RGB channels (Mask-R / Mask-G / Mask-B), Gamma, Contrast
- **Emulsion Concentration Correction**: Per-channel contrast (Contrast R / G / B) for fine-tuning tonality
- **Exposure**: Exposure compensation adjustment
- **White Balance**: Auto white balance or manual temperature and tint control
- All parameters support precise numeric input and step adjustment

#### Image Operations

- Main image zoom and pan (Ctrl+scroll, pinch gestures, keyboard shortcuts)
- Right-click context menu:
  - Copy / Paste parameters
  - Apply preset
  - Pick mask color
  - Select white-point area
  - Rotate (clockwise 90°, counter-clockwise 90°, 180°)
  - Reset image
- Real-time histogram preview

#### Batch Processing

- **Apply**: Apply current parameters to the displayed image
- **Apply All**: Batch-apply basic parameters to all images in the directory
- **Save All**: Export all images with applied parameters

### Languages & Theme

- 14 interface languages
- Dark and light theme, synced with system appearance

---

## Command-Line Tool (CLI)

### Process a Single Negative

```powershell
openlucky.exe film -i input.tif -o output.jpg -c config.yaml -p kodak_ultramax_400
```

### Batch Process Negatives

```powershell
# Output to input/output directory
openlucky.exe filmbatch -i ./input

# Specify output directory
openlucky.exe filmbatch -i ./input -o ./output

# Use custom config and preset
openlucky.exe filmbatch -i ./input -o ./output -c config.yaml -p kodak_ultramax_400
```

### Format Conversion

```powershell
openlucky.exe tiff2jpeg -i input.tif -o output.jpg
```

### CLI Arguments

#### openlucky.py film

Process a single film negative.

| Argument | Short | Required | Description |
|----------|-------|----------|-------------|
| `--input` | `-i` | Yes | Input negative file path (.tif, .tiff, .jpg) |
| `--output` | `-o` | Yes | Output file path |
| `--config` | `-c` | Yes | Preset config file (YAML) path |
| `--preset` | `-p` | No | Preset name (default: kodak_ultramax_400) |

#### openlucky.py filmbatch

Batch process film negatives.

| Argument | Short | Required | Description |
|----------|-------|----------|-------------|
| `--input` | `-i` | Yes | Input image directory |
| `--output` | `-o` | No | Output directory (default: `output` subdirectory under input) |
| `--config` | `-c` | No | Preset config file (YAML) path (auto-detected if omitted) |
| `--preset` | `-p` | No | Preset name (default: kodak_ultramax_400) |

Supported formats: `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.bmp`

#### openlucky.py tiff2jpeg

Convert TIFF to JPEG.

| Argument | Short | Required | Description |
|----------|-------|----------|-------------|
| `--input` | `-i` | Yes | Input TIFF file path |
| `--output` | `-o` | Yes | Output JPEG file path |

---

## Configuration

The `config.yaml` file uses YAML format. Each preset contains the following parameters:

```yaml
presets:
  preset_name:
    mask_r: 215      # Film base red channel reference (0-255)
    mask_g: 145      # Film base green channel reference (0-255)
    mask_b: 95       # Film base blue channel reference (0-255)
    contrast: 1.15   # Contrast fine-tuning (recommended: 1.0-1.5)
    gamma: 0.45      # Gamma correction (recommended: 0.4-2.2)
```

### Parameter Details

- **mask_r/mask_g/mask_b**: Reference values for each color mask channel, used for normalization
- **contrast**: Contrast coefficient, 1.0 means no adjustment
- **gamma**: Gamma correction, <1.0 brightens shadows, >1.0 darkens shadows

## Built-in Presets

| Preset Name | Film Type | Characteristics |
|-------------|-----------|-----------------|
| `kodak_gold_200` | Kodak Gold 200 | Consumer film, warm tones |
| `fuji_c200` | Fuji C200 | Consumer film, cool tones |
| `kodak_ultramax_400` | Kodak UltraMax 400 | High-speed consumer film, vivid colors |
| `fujifilm_c400` | Fujifilm C400 | Consumer high-speed film, pinkish skin tones |
| `vision3_50d_5203` | Kodak Vision3 50D | Daylight cinema film, ultra-fine grain |
| `vision3_250d_5207` | Kodak Vision3 250D | Daylight cinema film, all-purpose |
| `vision3_200t_5213` | Kodak Vision3 200T | Tungsten cinema film |
| `vision3_500t_5219` | Kodak Vision3 500T | High-speed tungsten cinema film |
| `agfa_turia_100s_xx1` | Agfa Turia 100S | Consumer film, high contrast |

## Custom Presets

Add your own presets in `config.yaml`:

```yaml
presets:
  my_custom_film:
    mask_r: 200
    mask_g: 140
    mask_b: 100
    contrast: 1.1
    gamma: 0.5
```

Use custom presets:

```powershell
# Single image
openlucky.exe film -i input.tif -o output.jpg -c config.yaml -p my_custom_film

# Batch processing
openlucky.exe filmbatch -i ./input -o ./output -c config.yaml -p my_custom_film
```

## How It Works

1. **Color Mask Removal** - Normalize each channel using preset mask values
2. **Color Inversion** - Convert the negative image to a positive
3. **Gamma Correction** - Adjust the tone curve for natural shadow detail
4. **Auto Levels** - Adjust black and white points based on histogram statistics
5. **Contrast Adjustment** - Fine-tune image contrast

## License

Apache License 2.0 — see the LICENSE file for details
