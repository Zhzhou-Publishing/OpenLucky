from PIL import Image, ImageOps


def convert_tiff_to_jpeg(input_path, output_path):
    try:
        with Image.open(input_path) as img:
            # 1. 尝试纠正图片方向，但捕获可能发生的 EXIF 错误
            try:
                # 显式调用 exif_transpose，如果元数据损坏则跳过
                img = ImageOps.exif_transpose(img)
            except Exception as e:
                print(f"⚠️ Warning: Cannot process EXIF orientation data, will process as-is. Error: {e}")

            # 2. 统一转换为 RGB 模式
            # 使用 list(img.getdata()) 强制加载像素数据，跳过元数据处理
            rgb_img = img.convert('RGB')

            # 3. 保存为 JPEG
            # 这里不传递 exif=img.info.get('exif') 以免再次触发错误
            rgb_img.save(output_path, 'JPEG', quality=90)

        print(f"✅ Conversion successful: {output_path}")

    except Exception as e:
        print(f"❌ Core error: {e}")
        import traceback
        traceback.print_exc()
