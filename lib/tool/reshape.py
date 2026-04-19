import io
import rawpy
import tifffile
import numpy as np
import cv2
from pathlib import Path


def is_convex_quadrilateral(points):
    """
    检查四个点是否构成凸四边形

    Args:
        points: 四个点的列表，格式为 [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
               点的顺序应为 p1->p2->p3->p4->p1

    Returns:
        bool: 如果是凸四边形返回True，否则返回False
    """
    points = np.array(points, dtype=np.float32)

    # 计算叉积符号
    def cross_product(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    n = len(points)
    prev_sign = 0

    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        c = points[(i + 2) % n]

        cross = cross_product(a, b, c)

        if cross != 0:
            if prev_sign == 0:
                prev_sign = 1 if cross > 0 else -1
            elif (cross > 0 and prev_sign < 0) or (cross < 0 and prev_sign > 0):
                return False

    # 检查是否有三个点共线
    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        c = points[(i + 2) % n]

        if cross_product(a, b, c) == 0:
            return False

    return True


def parse_point(point_str, point_name):
    """
    解析点坐标字符串

    Args:
        point_str: 点坐标字符串，格式为 "x,y"
        point_name: 点名称，用于错误信息

    Returns:
        tuple: (x, y)

    Raises:
        ValueError: 如果格式无效
    """
    try:
        parts = point_str.split(',')
        if len(parts) != 2:
            raise ValueError(f"Invalid {point_name} format. Expected 'x,y', got '{point_str}'")
        x = int(parts[0].strip())
        y = int(parts[1].strip())
        if x < 0 or y < 0:
            raise ValueError(f"{point_name} coordinates must be non-negative, got ({x}, {y})")
        return (x, y)
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Invalid {point_name} coordinates. Expected integers, got '{point_str}'")
        raise


def parse_shape(shape_str):
    """
    解析输出画布尺寸字符串

    Args:
        shape_str: 画布尺寸字符串，格式为 "width,height"

    Returns:
        tuple: (width, height)

    Raises:
        ValueError: 如果格式无效
    """
    try:
        parts = shape_str.split(',')
        if len(parts) != 2:
            raise ValueError(f"Invalid shape format. Expected 'width,height', got '{shape_str}'")
        width = int(parts[0].strip())
        height = int(parts[1].strip())
        if width <= 0 or height <= 0:
            raise ValueError(f"Shape dimensions must be positive, got {width}x{height}")
        return (width, height)
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Invalid shape dimensions. Expected integers, got '{shape_str}'")
        raise


def read_image_safe(filepath):
    """
    读取图像文件，支持多种格式（8位、16位TIFF、RAW等）

    Args:
        filepath: 图像文件路径

    Returns:
        tuple: (image_array, is_16bit, is_raw)
               image_array: 图像数据数组
               is_16bit: 是否为16位图像
               is_raw: 是否为RAW格式
    """
    try:
        from cmd.constants.image_formats import RAW_EXTENSIONS
    except ImportError:
        RAW_EXTENSIONS = {".cr2", ".arw", ".nef", ".dng", ".orf", ".raf"}

    filepath = Path(filepath)
    ext = filepath.suffix.lower()
    is_raw = ext in RAW_EXTENSIONS

    if is_raw:
        # RAW格式处理
        with open(filepath, "rb") as f:
            raw_bytes = f.read()
        with rawpy.imread(io.BytesIO(raw_bytes)) as raw:
            demosaic_algorithm = rawpy.DemosaicAlgorithm.AAHD
            img = raw.postprocess(
                demosaic_algorithm=demosaic_algorithm,
                fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                gamma=(1, 1),
                no_auto_bright=True,
                output_bps=16,
                use_camera_wb=True,
                bright=1.0,
            )
        return img, True, True

    # TIFF格式优先使用tifffile
    if ext in (".tif", ".tiff"):
        img_raw = None
        if tifffile:
            try:
                img_raw = tifffile.imread(str(filepath))
            except Exception as e:
                print(f"Tifffile read failed (maybe missing imagecodecs?): {e}")

        # 如果tifffile读取失败，尝试OpenCV
        if img_raw is None:
            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
            img_raw = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
            if img_raw is not None:
                img_raw = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB)

        if img_raw is None:
            raise ValueError(f"Cannot decode TIFF image: {filepath}")

        is_16bit = img_raw.dtype == np.uint16
        return img_raw, is_16bit, False

    # 普通格式使用OpenCV
    file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
    img_raw = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
    if img_raw is None:
        raise ValueError(f"Cannot decode image: {filepath}")

    is_16bit = img_raw.dtype == np.uint16
    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB)
    return img, is_16bit, False


def write_image_safe(filepath, img, is_16bit=False):
    """
    安全写入图像文件，支持中文路径

    Args:
        filepath: 输出文件路径
        img: 图像数组（RGB格式）
        is_16bit: 是否为16位图像

    Returns:
        bool: 成功返回True，失败返回False
    """
    try:
        filepath = Path(filepath)
        out_ext = filepath.suffix.lower()

        # 创建输出目录
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if is_16bit or out_ext in (".tif", ".tiff"):
            # 16位或TIFF格式
            output_img = img if img.dtype == np.uint16 else (img * 65535).astype(np.uint16)

            # 优先使用tifffile
            if out_ext in (".tif", ".tiff") and tifffile:
                try:
                    tifffile.imwrite(str(filepath), output_img, compression="zlib")
                    return True
                except Exception as e:
                    print(f"Tifffile save failed: {e}, falling back to OpenCV")

            # OpenCV回退
            output_img_bgr = cv2.cvtColor(output_img, cv2.COLOR_RGB2BGR)
            return cv2.imwrite(str(filepath), output_img_bgr)
        else:
            # 8位格式
            if img.dtype == np.uint16:
                output_img = (img / 256).astype(np.uint8)
            else:
                output_img = img
            output_img_bgr = cv2.cvtColor(output_img, cv2.COLOR_RGB2BGR)

            params = []
            if out_ext in (".jpg", ".jpeg"):
                params = [cv2.IMWRITE_JPEG_QUALITY, 95]
            elif out_ext == ".png":
                params = [cv2.IMWRITE_PNG_COMPRESSION, 6]
            elif out_ext == ".webp":
                params = [cv2.IMWRITE_WEBP_QUALITY, 95]

            return cv2.imwrite(str(filepath), output_img_bgr, params)
    except Exception as e:
        print(f"Error writing image: {e}")
        return False


def reshape_image(input_path, output_path, point1, point2, point3, point4, shape):
    """
    四点形状校正

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        point1: 左上角裁切锚点 (x, y)
        point2: 右上角裁切锚点 (x, y)
        point3: 右下角裁切锚点 (x, y)
        point4: 左下角裁切锚点 (x, y)
        shape: 输出画布尺寸 (width, height)

    Returns:
        bool: 成功返回True，失败返回False
    """
    try:
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            print(f"Error: Input file does not exist: {input_path}")
            return False

        # 读取图像
        img, is_16bit, is_raw = read_image_safe(input_path)
        print(f"Loaded image: {img.shape}, dtype={img.dtype}, 16bit={is_16bit}")

        # 验证点坐标是否在图像范围内
        height, width = img.shape[:2]
        points = [point1, point2, point3, point4]
        for i, point in enumerate(points, 1):
            x, y = point
            if x >= width or y >= height:
                print(f"Error: Point{i} ({x}, {y}) is outside image bounds ({width}x{height})")
                return False

        # 验证是否是凸四边形
        if not is_convex_quadrilateral(points):
            print("Error: Points do not form a convex quadrilateral")
            return False
        print("Points form a valid convex quadrilateral")

        # 创建透视变换矩阵
        # 源点：用户指定的四个点
        src_points = np.array(points, dtype=np.float32)

        # 目标点：画布的四个角
        dst_width, dst_height = shape
        dst_points = np.array([
            [0, 0],              # 左上
            [dst_width - 1, 0],  # 右上
            [dst_width - 1, dst_height - 1],  # 右下
            [0, dst_height - 1]  # 左下
        ], dtype=np.float32)

        # 计算透视变换矩阵
        M = cv2.getPerspectiveTransform(src_points, dst_points)

        # 创建白色画布
        if is_16bit:
            white_canvas = np.full((dst_height, dst_width, 3), 65535, dtype=np.uint16)
        else:
            white_canvas = np.full((dst_height, dst_width, 3), 255, dtype=np.uint8)

        # 应用透视变换
        warped = cv2.warpPerspective(img, M, (dst_width, dst_height))

        # 创建掩膜（非透明区域）
        mask = cv2.warpPerspective(
            np.ones((height, width), dtype=np.uint8) * 255,
            M, (dst_width, dst_height)
        )
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)

        # 合并：将变换后的图像叠加到白色画布上
        if is_16bit:
            mask_3ch = (mask_3ch / 255 * 65535).astype(np.uint16)
            result = np.where(mask_3ch > 0, warped, white_canvas).astype(np.uint16)
        else:
            result = np.where(mask_3ch > 0, warped, white_canvas).astype(np.uint8)

        # 保存结果
        if write_image_safe(output_path, result, is_16bit or is_raw):
            print(f"Successfully reshaped and saved to: {output_path}")
            return True
        else:
            print("Error: Failed to save output image")
            return False

    except ValueError as e:
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"Error reshaping image: {e}")
        import traceback
        traceback.print_exc()
        return False
