import cv2
import numpy as np
import yaml


def process_film_with_params(input_path, output_path, preset_mask_r, preset_mask_g, preset_mask_b, preset_gamma=1.0, preset_contrast=1.0):
    # 1. Read image (supports TIFF, allows reading 16bit)
    img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"Error: Cannot read input file '{input_path}'")
        return

    # 转换为浮点数进行高精度计算
    img = img.astype(np.float32)

    # 2. 去色罩 (Color Mask Removal)
    # 根据预设值归一化各个通道
    img[:, :, 0] /= (preset_mask_b / 255.0)  # Blue
    img[:, :, 1] /= (preset_mask_g / 255.0)  # Green
    img[:, :, 2] /= (preset_mask_r / 255.0)  # Red
    img = np.clip(img, 0, 255)

    # 3. 颜色反转
    img = 255.0 - img

    # 4. Gamma 修正 (让暗部细节更自然)
    if preset_gamma != 1.0:
        img = np.power(img / 255.0, preset_gamma) * 255.0

    # 5. 自动色阶与对比度微调
    for i in range(3):
        low = np.percentile(img[:, :, i], 0.5)  # 忽略极小比例的黑场噪点
        high = np.percentile(img[:, :, i], 99.5)  # 忽略极小比例的白场噪点
        img[:, :, i] = np.clip((img[:, :, i] - low) * (255.0 / (high - low + 1e-5)) * preset_contrast, 0, 255)

    # 6. Save result
    img_final = img.astype(np.uint8)
    cv2.imwrite(str(output_path), img_final)
    print(f"Processing successful! Result saved to: {output_path}")
    
    return {
        "mask_r": preset_mask_r,
        "mask_g": preset_mask_g,
        "mask_b": preset_mask_b,
        "gamma": preset_gamma,
        "contrast": preset_contrast
    }


def process_film(input_path, output_path, config_path, preset_name="kodak_ultramax_400"):
    # 1. 加载配置
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        preset = config['presets'].get(preset_name)
        if not preset:
            print(f"Error: Preset '{preset_name}' not found in config file")
            return
    except Exception as e:
        print(f"Cannot read config file: {e}")
        return

    # 2. 调用核心处理函数
    process_film_with_params(
        input_path,
        output_path,
        preset_mask_b=preset['mask_b'],
        preset_mask_g=preset['mask_g'],
        preset_mask_r=preset['mask_r'],
        preset_gamma=preset.get('gamma', 1.0),
        preset_contrast=preset.get('contrast', 1.0)
    )

    return config
