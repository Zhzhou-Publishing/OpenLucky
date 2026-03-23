import cv2
import numpy as np
import yaml


def process_film_with_params(input_path, output_path, preset_mask_r, preset_mask_g, preset_mask_b, preset_gamma=1.0, preset_contrast=1.0):
    # 1. 读取图片 (UNCHANGED 保持原始位深)
    img = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"Error: Cannot read input file '{input_path}'")
        return

    # 判断输入是 8位 还是 16位，并统一归一化到 0.0 - 1.0 空间
    # 这一步是支持高位深的关键
    max_input_val = 65535.0 if img.dtype == np.uint16 else 255.0
    img = img.astype(np.float32) / max_input_val

    # 2. 去色罩 (在 0-1 空间操作)
    # 假设输入的参数 mask_r/g/b 依然是用户习惯的 0-255 范围
    img[:, :, 0] /= (preset_mask_b / 255.0)  # Blue
    img[:, :, 1] /= (preset_mask_g / 255.0)  # Green
    img[:, :, 2] /= (preset_mask_r / 255.0)  # Red
    
    # 这一步 clip 很重要，防止除法后数值溢出 1.0
    img = np.clip(img, 0, 1.0)

    # 3. 颜色反转 (在 0-1 空间即为 1.0 - img)
    img = 1.0 - img

    # 4. Gamma 修正
    if preset_gamma != 1.0:
        # 在 0-1 空间进行幂运算，精度最高
        img = np.power(img, preset_gamma)

    # 5. 自动色阶与对比度微调
    for i in range(3):
        low = np.percentile(img[:, :, i], 0.5) 
        high = np.percentile(img[:, :, i], 99.5)
        # 线性拉伸并应用对比度
        img[:, :, i] = np.clip((img[:, :, i] - low) * (1.0 / (high - low + 1e-5)) * preset_contrast, 0, 1.0)
    # 6. 根据输入位深，动态决定输出位深
    if max_input_val == 255.0:
        # 输入是 8 位，输出 8 位
        img_final = (img * 255.0).astype(np.uint8)
        print(f"8-bit Processing successful!")
    else:
        # 输入是 16 位，输出 16 位
        img_final = (img * 65535.0).astype(np.uint16)
        print(f"16-bit Processing successful!")

    # 7. 保存文件
    # 注意：cv2.imwrite 保存 .tif 时会自动识别 uint16
    cv2.imwrite(str(output_path), img_final)
    
    print(f"8-bit/16-bit Processing successful! Saved to: {output_path}")
    
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
