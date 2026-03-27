import io
import rawpy
import numpy as np
import cv2


def process_film_bytestream_with_params(
    input_bytes,
    preset_mask_r,
    preset_mask_g,
    preset_mask_b,
    preset_gamma=1.0,
    preset_contrast=1.0,
    is_raw=False,
):
    """
    处理字节流图片，支持 RAW 格式开关
    """
    # 1. 显式解码图片
    if is_raw:
        # 处理 RAW 格式：使用 rawpy 引擎
        with rawpy.imread(io.BytesIO(input_bytes)) as raw:
            # postprocess 得到的是 RGB 顺序的 uint16 数组
            img = (
                raw.postprocess(
                    user_qual=10,
                    gamma=(1, 1),  # 保持线性
                    no_auto_bright=True,  # 禁止自动亮度
                    output_bps=16,  # 16位精度
                ).astype(np.float32)
                / 65535.0
            )
        is_16bit_target = True
    else:
        # 处理普通格式：使用 OpenCV 引擎
        nparr = np.frombuffer(input_bytes, np.uint8)
        img_raw = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if img_raw is None:
            return None

        # 统一转为 RGB (OpenCV 默认是 BGR)
        img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB).astype(np.float32)

        max_val = 65535.0 if img_raw.dtype == np.uint16 else 255.0
        img /= max_val
        is_16bit_target = img_raw.dtype == np.uint16

    # 2. 去色罩 (在 0-1 空间操作)
    # 此时 img 确定是 RGB 顺序
    img[:, :, 0] /= preset_mask_r / 255.0  # Red
    img[:, :, 1] /= preset_mask_g / 255.0  # Green
    img[:, :, 2] /= preset_mask_b / 255.0  # Blue
    img = np.clip(img, 0, 1.0)

    # 3. 颜色反转 (在 0-1 空间即为 1.0 - img)
    img = 1.0 - img

    # 4. Gamma 修正
    # 对于线性 RAW，建议输入 0.45 左右；对于已带 Gamma 的图片，建议 1.0 左右微调
    if preset_gamma != 1.0:
        # 在 0-1 空间进行幂运算，精度最高
        img = np.power(img, preset_gamma)

    # 5. 自动色阶与对比度微调
    for i in range(3):
        low = np.percentile(img[:, :, i], 0.5)
        high = np.percentile(img[:, :, i], 99.5)
        # 线性拉伸并应用对比度
        img[:, :, i] = np.clip(
            (img[:, :, i] - low) * (1.0 / (high - low + 1e-5)) * preset_contrast, 0, 1.0
        )

    # 6. 编码回字节流
    # 记得转回 BGR 供 OpenCV 编码输出
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    if is_16bit_target:
        # 输出 16bit TIFF 保留细节
        success, encoded_img = cv2.imencode(
            ".tif", (img_bgr * 65535.0).astype(np.uint16)
        )
    else:
        # 输出 8bit PNG
        success, encoded_img = cv2.imencode(".png", (img_bgr * 255.0).astype(np.uint8))

    return encoded_img.tobytes() if success else None


def process_film_with_params(
    input_path,
    output_path,
    preset_mask_r,
    preset_mask_g,
    preset_mask_b,
    preset_gamma=1.0,
    preset_contrast=1.0,
):
    # 1. 读取输入文件为字节流
    try:
        with open(input_path, "rb") as f:
            input_bytes = f.read()
    except Exception as e:
        print(f"Error: Cannot read input file '{input_path}': {e}")
        return

    # 支持 raw 格式开关，判断文件扩展名
    ext = input_path.suffix.lower()
    raw_extensions = [".arw", ".cr2", ".cr3", ".nef", ".dng", ".orf", ".raf"]

    # 2. 调用字节流处理函数
    output_bytes = process_film_bytestream_with_params(
        input_bytes,
        preset_mask_r=preset_mask_r,
        preset_mask_g=preset_mask_g,
        preset_mask_b=preset_mask_b,
        preset_gamma=preset_gamma,
        preset_contrast=preset_contrast,
        is_raw=ext in raw_extensions,
    )

    # 3. 将输出字节流写入文件
    if output_bytes is None:
        print(f"Error: Failed to process image from '{input_path}'")
        return

    try:
        with open(output_path, "wb") as f:
            f.write(output_bytes)
        print(f"Successfully saved to: {output_path}")
    except Exception as e:
        print(f"Error: Cannot write output file '{output_path}': {e}")
