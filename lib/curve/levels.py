import io
import rawpy
import numpy as np
import cv2
from pathlib import Path


def levels_clip(
    input_path, output_path, shadows=0, highlights=0, channel="all", mode="clip-stretch"
):
    """
    OpenLucky: 胶片数字化色阶/剪裁工具

    Args:
        input_path: 输入图像路径
        output_path: 输出图像路径
        shadows: 暗部裁切千分比 (0-1000)，5 表示 0.5%
        highlights: 亮部裁切千分比 (0-1000)
        channel: 作用通道 ['all', 'red', 'green', 'blue']
        mode: 'clip-only' (仅剪裁) 或 'clip-stretch' (剪裁并拉伸)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return False

    # 1. 读取与解码
    # ---------------------------------------------------------
    from cmd.constants.image_formats import RAW_EXTENSIONS  # 保持你的引用

    ext = input_path.suffix.lower()
    is_raw = ext in RAW_EXTENSIONS

    if is_raw:
        with open(input_path, "rb") as f:
            raw_bytes = f.read()
        with rawpy.imread(io.BytesIO(raw_bytes)) as raw:
            # 使用胶片处理常用的 AAHD 算法
            demosaic_algorithm = rawpy.DemosaicAlgorithm.AAHD
            img = (
                raw.postprocess(
                    demosaic_algorithm=demosaic_algorithm,
                    fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                    gamma=(1, 1),  # 保持线性
                    no_auto_bright=True,  # 禁止自动提亮
                    output_bps=16,  # 16位输出
                    use_camera_wb=True,
                    bright=1.0,
                ).astype(np.float32)
                / 65535.0
            )
        is_16bit = True
    else:
        # 使用 np.fromfile 以支持中文路径
        file_bytes = np.fromfile(str(input_path), dtype=np.uint8)
        img_raw = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
        if img_raw is None:
            print(f"Error: Cannot decode image: {input_path}")
            return False

        is_16bit = img_raw.dtype == np.uint16
        # 转为 RGB float32 [0, 1]
        img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB).astype(np.float32)
        img /= 65535.0 if is_16bit else 255.0

    # 2. 确定通道范围
    # ---------------------------------------------------------
    if channel == "all":
        channel_indices = [0, 1, 2]
    elif channel == "red":
        channel_indices = [0]
    elif channel == "green":
        channel_indices = [1]
    elif channel == "blue":
        channel_indices = [2]
    else:
        print(f"Error: Unknown channel {channel}")
        return False

    # 3. 核心算法逻辑：分通道计算阈值
    # ---------------------------------------------------------
    shadow_pct = shadows / 1000.0
    highlight_pct = highlights / 1000.0

    for ch in channel_indices:
        ch_data = img[:, :, ch]

        # 使用 percentile 代替排序，大幅提升性能
        # 注意：percentile 接受的是 0-100 的数值
        s_thresh = np.percentile(ch_data, shadow_pct * 100)
        h_thresh = np.percentile(ch_data, (1.0 - highlight_pct) * 100)

        # 剪裁：低于阴影阈值设为 0，高于高光阈值设为 1
        ch_img = img[:, :, ch]
        ch_img[ch_img <= s_thresh] = 0.0
        ch_img[ch_img >= h_thresh] = 1.0

        if mode == “clip-stretch”:
            # 拉伸：将中间值线性映射到 [0, 1]
            mask = (ch_img > 0.0) & (ch_img < 1.0)
            if s_thresh < h_thresh:
                ch_img[mask] = (ch_img[mask] - s_thresh) / (h_thresh - s_thresh)

        img[:, :, ch] = ch_img

    # 统一进行溢出保护
    img = np.clip(img, 0.0, 1.0)

    # 4. 保存结果
    # ---------------------------------------------------------
    # 转回 BGR 用于 OpenCV 保存
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    out_ext = output_path.suffix.lower()

    # 决定输出位深
    # 如果原图是 16位、RAW 或者是指定输出为 TIFF，则保存为 16-bit
    if is_16bit or is_raw or out_ext in (".tif", ".tiff"):
        output_img = (img_bgr * 65535.0).astype(np.uint16)
        # TIFF 默认不压缩或使用 LZW
        success, encoded = cv2.imencode(".tif", output_img)
    else:
        output_img = (img_bgr * 255.0).astype(np.uint8)
        if out_ext in (".jpg", ".jpeg"):
            params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        elif out_ext == ".webp":
            params = [cv2.IMWRITE_WEBP_QUALITY, 95]
        else:
            params = []
        success, encoded = cv2.imencode(
            out_ext if out_ext else ".png", output_img, params
        )

    if not success:
        print("Error: Failed to encode output image")
        return False

    try:
        with open(output_path, "wb") as f:
            f.write(encoded.tobytes())
        print(f"Successfully processed: {input_path.name} -> {output_path.name}")
        return True
    except Exception as e:
        print(f"Error writing to file: {e}")
        return False
