import argparse

from lib.tiff_to_jpeg import convert_tiff_to_jpeg


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    convert_tiff_to_jpeg(args.input, args.output)
