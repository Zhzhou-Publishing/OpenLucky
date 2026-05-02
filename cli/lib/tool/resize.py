import rawpy
import cv2
import numpy as np
import shutil
from pathlib import Path

from cli.constants.image_formats import RAW_EXTENSIONS

# 支持的边选项
EDGE_OPTIONS = {'width', 'height', 'long-edge', 'short-edge'}

# 支持的缩放模式
MODE_OPTIONS = {'ratio', 'fixed-value'}


def read_image_safe(filepath):
    """
    Read image file safely, supporting Chinese paths on Windows.

    Uses numpy.fromfile + cv2.imdecode to bypass OpenCV's
    Unicode path limitations on Windows.

    Args:
        filepath: Path to the image file

    Returns:
        numpy.ndarray: Image data, or None if failed
    """
    try:
        # Read file as bytes
        with open(filepath, 'rb') as f:
            file_bytes = np.fromfile(f, dtype=np.uint8)

        # Decode using OpenCV
        img = cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
        return img
    except Exception:
        return None


def write_image_safe(filepath, encoded_bytes):
    """
    Write image file safely, supporting Chinese paths on Windows.

    Uses np.tofile to bypass potential file writing issues.

    Args:
        filepath: Path to save the image file
        encoded_bytes: Encoded image bytes from cv2.imencode

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create output directory
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # Write using numpy's tofile method
        np.array(list(encoded_bytes.tobytes()), dtype=np.uint8).tofile(filepath)
        return True
    except Exception as e:
        print(f"Error writing file: {e}")
        return False


def validate_output_filename(input_path, output_path):
    """
    验证输出文件名是否合规

    规则：
    - 非RAW格式：输出文件名必须与输入文件名相同
    - RAW格式：输出可以是原文件名，或原文件名+.tif/.tiff

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径

    Returns:
        bool: 是否合规

    Raises:
        ValueError: 文件名不合规时抛出
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    input_ext = input_path.suffix.lower()
    is_raw = input_ext in RAW_EXTENSIONS

    if is_raw:
        # RAW格式：输出可以是原文件名，或原文件名+.tif/.tiff
        output_ext = output_path.suffix.lower()
        filename_match = output_path.name == input_path.name

        if filename_match:
            # 输出文件名与输入完全相同
            return True
        elif output_ext in {'.tif', '.tiff'}:
            # 输出是原文件名+.tif/.tiff
            return output_path.stem == input_path.name
        else:
            raise ValueError(
                f"Invalid output filename for RAW format. "
                f"Expected '{input_path.name}' or '{input_path.name}.tif'/'{input_path.name}.tiff', "
                f"got '{output_path.name}'"
            )
    else:
        # 非RAW格式：输出文件名必须与输入文件名相同
        if output_path.name != input_path.name:
            raise ValueError(
                f"Invalid output filename. "
                f"Output filename must match input filename. "
                f"Expected '{input_path.name}', got '{output_path.name}'"
            )
        return True


def calculate_new_dimensions(original_width, original_height, edge, mode, value):
    """
    根据参数计算新的图片尺寸

    Args:
        original_width: 原始宽度
        original_height: 原始高度
        edge: 缩放依据的边 {width,height,long-edge,short-edge}
        mode: 缩放模式 {ratio,fixed-value}
        value: 缩放值

    Returns:
        tuple: (new_width, new_height)

    Raises:
        ValueError: 参数不合法时抛出
    """
    # 验证参数
    if edge not in EDGE_OPTIONS:
        raise ValueError(f"Invalid edge value. Expected one of {EDGE_OPTIONS}, got '{edge}'")

    if mode not in MODE_OPTIONS:
        raise ValueError(f"Invalid mode value. Expected one of {MODE_OPTIONS}, got '{mode}'")

    # 根据模式验证value
    if mode == 'ratio':
        if not (0 < value <= 1):
            raise ValueError(f"Invalid value for ratio mode. Expected (0, 1], got {value}")
    elif mode == 'fixed-value':
        if not (value > 0 and isinstance(value, (int, float)) and value == int(value)):
            raise ValueError(
                f"Invalid value for fixed-value mode. Expected positive integer, got {value}"
            )
        value = int(value)

    # 确定长边和短边
    long_edge = max(original_width, original_height)
    short_edge = min(original_width, original_height)

    # 计算新的尺寸
    if mode == 'ratio':
        # 按比例缩放
        new_width = int(original_width * value)
        new_height = int(original_height * value)
    else:
        # 按固定值缩放
        if edge == 'width':
            new_width = value
            scale_ratio = value / original_width
            new_height = int(original_height * scale_ratio)
        elif edge == 'height':
            new_height = value
            scale_ratio = value / original_height
            new_width = int(original_width * scale_ratio)
        elif edge == 'long-edge':
            scale_ratio = value / long_edge
            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)
        elif edge == 'short-edge':
            scale_ratio = value / short_edge
            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)

    return new_width, new_height


def resize_image(input_path, output_path, edge='long-edge', mode='fixed-value', value=None):
    """
    调整图片大小

    当 value 为 None 时，不执行缩放：
    - 非RAW图片：直接复制到输出路径
    - RAW图片：转换为TIFF放入输出路径

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        edge: 缩放依据的边，默认 long-edge
        mode: 缩放模式，默认 fixed-value
        value: 缩放值，None 表示不缩放

    Returns:
        bool: 成功返回True，失败返回False
    """
    try:
        input_path = Path(input_path)
        output_path = Path(output_path)

        # 验证输出文件名
        output_filename_valid = validate_output_filename(input_path, output_path)
        if not output_filename_valid:
            print("invalid output filename")
            return False

        # 确定是否为RAW格式
        input_ext = input_path.suffix.lower()
        is_raw = input_ext in RAW_EXTENSIONS

        # 无缩放模式：非RAW直接复制，RAW转TIFF
        if value is None:
            if is_raw:
                # RAW格式：照常做demosaic后转TIFF放入工作目录
                with rawpy.imread(str(input_path)) as raw:
                    img = raw.postprocess(
                        demosaic_algorithm=(
                            rawpy.DemosaicAlgorithm.DHT if input_ext == '.raf'
                            else rawpy.DemosaicAlgorithm.AAHD
                        ),
                        fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                        gamma=(1, 1),
                        no_auto_bright=True,
                        output_bps=16,
                        use_camera_wb=True,
                        bright=1.0,
                    )

                output_path = output_path.with_suffix('.tif')
                # RGB → BGR for cv2.imencode
                if len(img.shape) == 3 and img.shape[2] == 3:
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                else:
                    img_bgr = img

                success, encoded_img = cv2.imencode('.tif', img_bgr)
                if not success:
                    print(f"Error: Failed to encode TIFF to '{output_path}'")
                    return False

                if not write_image_safe(str(output_path), encoded_img):
                    return False

                print(f"RAW converted to TIFF (no resize): {output_path}")
                return True
            else:
                # 非RAW格式：直接复制到工作目录
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(input_path), str(output_path))
                print(f"Copied (no resize): {output_path}")
                return True

        # 读取图片
        if is_raw:
            # RAW格式：使用rawpy读取
            with rawpy.imread(str(input_path)) as raw:
                img = raw.postprocess(
                    demosaic_algorithm=(
                        rawpy.DemosaicAlgorithm.DHT if input_ext == '.raf'
                        else rawpy.DemosaicAlgorithm.AAHD
                    ),
                    fbdd_noise_reduction=rawpy.FBDDNoiseReductionMode.Off,
                    gamma=(1, 1),
                    no_auto_bright=True,
                    output_bps=16,
                    use_camera_wb=True,
                    bright=1.0,
                )
        else:
            # 非RAW格式：使用安全方式读取（支持中文路径）
            img = read_image_safe(str(input_path))
            if img is None:
                print(f"Error: Failed to read image '{input_path}'")
                return False

            # 转换为RGB（OpenCV默认是BGR）
            if len(img.shape) == 3 and img.shape[2] == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 获取原始尺寸
        original_height, original_width = img.shape[:2]

        # 计算新尺寸
        new_width, new_height = calculate_new_dimensions(
            original_width, original_height, edge, mode, value
        )

        print(f"Original size: {original_width}x{original_height}")
        print(f"New size: {new_width}x{new_height}")

        # 缩放图片
        resized_img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # 确定输出格式
        output_ext = output_path.suffix.lower()

        # 如果是RAW格式，输出为TIFF
        if is_raw:
            output_ext = '.tif'
            output_path = output_path.with_suffix('.tif')
            # 转换回BGR进行编码
            resized_img_bgr = cv2.cvtColor(resized_img, cv2.COLOR_RGB2BGR)
            success, encoded_img = cv2.imencode('.tif', resized_img_bgr)
        else:
            # 非RAW格式：保持原格式
            if output_ext == '.jpg' or output_ext == '.jpeg':
                quality_param = [cv2.IMWRITE_JPEG_QUALITY, 95]
            elif output_ext == '.png':
                quality_param = [cv2.IMWRITE_PNG_COMPRESSION, 6]
            else:
                quality_param = []

            # 转换回BGR进行编码
            if len(resized_img.shape) == 3 and resized_img.shape[2] == 3:
                resized_img_bgr = cv2.cvtColor(resized_img, cv2.COLOR_RGB2BGR)
            else:
                resized_img_bgr = resized_img

            success, encoded_img = cv2.imencode(str(output_ext), resized_img_bgr, quality_param)

        if not success:
            print(f"Error: Failed to encode image to '{output_path}'")
            return False

        # 写入文件（使用安全方式支持中文路径）
        if not write_image_safe(str(output_path), encoded_img):
            return False

        print(f"Successfully resized and saved to: {output_path}")
        return True

    except ValueError as e:
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"Error resizing image: {e}")
        import traceback
        traceback.print_exc()
        return False
