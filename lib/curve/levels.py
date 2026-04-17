import io
import rawpy
import tifffile
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
    try:
        from cmd.constants.image_formats import RAW_EXTENSIONS
    except ImportError:
        RAW_EXTENSIONS = {".cr2", ".arw", ".nef", ".dng", ".orf", ".raf"}

    ext = input_path.suffix.lower()
    is_raw = ext in RAW_EXTENSIONS

    if is_raw:
        with open(input_path, "rb") as f:
            raw_bytes = f.read()
        with rawpy.imread(io.BytesIO(raw_bytes)) as raw:
            demosaic_algorithm = rawpy.DemosaicAlgorithm.AAHD
            img = (
                raw.postprocess(
                    demosaic_algorithm=demosaic_algorithm,
                    fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                    gamma=(1, 1),
                    no_auto_bright=True,
                    output_bps=16,
                    use_camera_wb=True,
                    bright=1.0,
                ).astype(np.float32)
                / 65535.0
            )
        is_16bit = True
    else:
        # 针对 TIFF 格式的健壮读取逻辑
        if ext in (".tif", ".tiff"):
            img_raw = None
            if tifffile:
                try:
                    img_raw = tifffile.imread(str(input_path))
                except Exception as e:
                    print(f"Tifffile read failed (maybe missing imagecodecs?): {e}")

            # 如果 tifffile 读取失败，尝试回退到 OpenCV
            if img_raw is None:
                file_bytes = np.fromfile(str(input_path), dtype=np.uint8)
                img_raw = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
                if img_raw is not None:
                    img_raw = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB)

            if img_raw is None:
                print(f"Error: All decoders failed for {input_path}")
                return False

            is_16bit = img_raw.dtype == np.uint16
            img = img_raw.astype(np.float32)
            img /= 65535.0 if is_16bit else 255.0
        else:
            # 普通格式使用 OpenCV
            file_bytes = np.fromfile(str(input_path), dtype=np.uint8)
            img_raw = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
            if img_raw is None:
                print(f"Error: Cannot decode image: {input_path}")
                return False

            is_16bit = img_raw.dtype == np.uint16
            img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB).astype(np.float32)
            img /= 65535.0 if is_16bit else 255.0

    # 2. 确定通道范围
    # ---------------------------------------------------------
    if channel == "all":
        channel_indices = [0, 1, 2]
    elif channel in ["red", "green", "blue"]:
        channel_indices = [{"red": 0, "green": 1, "blue": 2}[channel]]
    else:
        print(f"Error: Unknown channel {channel}")
        return False

    # 3. 核心算法逻辑：分通道计算阈值
    # ---------------------------------------------------------
    shadow_pct = shadows / 1000.0
    highlight_pct = highlights / 1000.0

    for ch in channel_indices:
        ch_data = img[:, :, ch]
        s_thresh = np.percentile(ch_data, shadow_pct * 100)
        h_thresh = np.percentile(ch_data, (1.0 - highlight_pct) * 100)

        if s_thresh >= h_thresh:
            continue

        if mode == "clip-stretch":
            img[:, :, ch] = (img[:, :, ch] - s_thresh) / (h_thresh - s_thresh)
        else:
            img[:, :, ch] = np.clip(img[:, :, ch], s_thresh, h_thresh)

    img = np.clip(img, 0.0, 1.0)

    # 4. 保存结果
    # ---------------------------------------------------------
    out_ext = output_path.suffix.lower()

    if is_16bit or is_raw or out_ext in (".tif", ".tiff"):
        output_img = (img * 65535.0).astype(np.uint16)
        if out_ext in (".tif", ".tiff") and tifffile:
            try:
                # 胶片数字化建议使用 zlib 或不压缩，保证兼容性
                tifffile.imwrite(str(output_path), output_img, compression="zlib")
                print(f"Successfully saved 16-bit TIFF: {output_path.name}")
                return True
            except Exception as e:
                print(f"Tifffile save failed: {e}, falling back to OpenCV")

        # OpenCV 回退保存
        output_img_bgr = cv2.cvtColor(output_img, cv2.COLOR_RGB2BGR)
        success = cv2.imwrite(str(output_path), output_img_bgr)
    else:
        # 8-bit 保存
        output_img_bgr = cv2.cvtColor((img * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR)
        params = []
        if out_ext in (".jpg", ".jpeg"):
            params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        elif out_ext == ".webp":
            params = [cv2.IMWRITE_WEBP_QUALITY, 95]
        success = cv2.imwrite(str(output_path), output_img_bgr, params)

    if success:
        print(f"Successfully processed: {input_path.name} -> {output_path.name}")
        return True
    else:
        print("Error: Failed to save output image")
        return False
