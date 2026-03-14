import cv2
import numpy as np
import yaml
import argparse
import sys
from pathlib import Path


def process_film(input_path, output_path, config_path, preset_name="kodak_ultramax_400"):
    # 1. 加载配置
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        preset = config['presets'].get(preset_name)
        if not preset:
            print(f"错误: 在配置文件中未找到预设 '{preset_name}'")
            return
    except Exception as e:
        print(f"无法读取配置文件: {e}")
        return

    # 2. 读取图片 (支持 TIFF, 允许读取 16bit)
    img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"错误: 无法读取输入文件 '{input_path}'")
        return

    # 转换为浮点数进行高精度计算
    img = img.astype(np.float32)

    # 3. 去色罩 (Color Mask Removal)
    # 根据预设值归一化各个通道
    img[:, :, 0] /= (preset['mask_b'] / 255.0)  # Blue
    img[:, :, 1] /= (preset['mask_g'] / 255.0)  # Green
    img[:, :, 2] /= (preset['mask_r'] / 255.0)  # Red
    img = np.clip(img, 0, 255)

    # 4. 颜色反转
    img = 255.0 - img

    # 5. Gamma 修正 (让暗部细节更自然)
    gamma = preset.get('gamma', 1.0)
    if gamma != 1.0:
        img = np.power(img / 255.0, gamma) * 255.0

    # 6. 自动色阶与对比度微调
    contrast = preset.get('contrast', 1.0)
    for i in range(3):
        low = np.percentile(img[:, :, i], 0.5)  # 忽略极小比例的黑场噪点
        high = np.percentile(img[:, :, i], 99.5)  # 忽略极小比例的白场噪点
        img[:, :, i] = np.clip((img[:, :, i] - low) * (255.0 / (high - low + 1e-5)) * contrast, 0, 255)

    # 7. 保存结果
    img_final = img.astype(np.uint8)
    cv2.imwrite(str(output_path), img_final)
    print(f"处理成功！结果已保存至: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="胶片负片转正处理工具 (Kodak UltraMax 400 优化)")

    parser.add_argument('--input', '-i', required=True, help='输入负片文件路径 (支持 .tif, .tiff, .jpg)')
    parser.add_argument('--output', '-o', required=True, help='输出文件保存路径')
    parser.add_argument('--config', '-c', required=True, help='预设配置文件 (yaml) 路径')
    parser.add_argument('--preset', '-p', default='kodak_ultramax_400',
                        help='使用的预设名称 (默认: kodak_ultramax_400)')

    args = parser.parse_args()

    input_file = Path(args.input)
    output_file = Path(args.output)
    config_file = Path(args.config)

    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)

    process_film(input_file, output_file, config_file, args.preset)


if __name__ == "__main__":
    main()