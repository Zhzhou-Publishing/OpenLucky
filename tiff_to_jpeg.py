import argparse

from PIL import Image, ImageOps


def convert_tiff_to_jpeg(input_path, output_path):
    try:
        with Image.open(input_path) as img:
            # 1. 尝试纠正图片方向，但捕获可能发生的 EXIF 错误
            try:
                # 显式调用 exif_transpose，如果元数据损坏则跳过
                img = ImageOps.exif_transpose(img)
            except Exception as e:
                print(f"⚠️ 警告：无法处理 EXIF 方向数据，将按原样处理。错误: {e}")

            # 2. 统一转换为 RGB 模式
            # 使用 list(img.getdata()) 强制加载像素数据，跳过元数据处理
            rgb_img = img.convert('RGB')

            # 3. 保存为 JPEG
            # 这里不传递 exif=img.info.get('exif') 以免再次触发错误
            rgb_img.save(output_path, 'JPEG', quality=90)

        print(f"✅ 转换成功：{output_path}")

    except Exception as e:
        print(f"❌ 核心错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    convert_tiff_to_jpeg(args.input, args.output)
