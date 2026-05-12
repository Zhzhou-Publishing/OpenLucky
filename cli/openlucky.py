import argparse
import json
import sys
import time
from pathlib import Path

import yaml

from cli.lib.process_film import process_film_with_params, process_film_bytestream_with_params
from cli.lib.tiff_to_jpeg import convert_tiff_to_jpeg
from cli.lib.raw_to_tiff import raw_to_tiff
from cli.lib.tool.resize import resize_image
from cli.lib.tool.reshape import reshape_image, parse_point, parse_shape
from cli.lib.tool.histogram import compute_histogram
from cli.lib.tool.pick import pick_color
from cli.lib.curve.levels import levels_clip
from cli.constants.image_formats import IMAGE_EXTENSIONS, RAW_EXTENSIONS


def save_preset_to_json(input_file, output_file, preset_config, preset_name, preset_label=None):
    """
    Save preset configuration to .preset.json file in the same directory as input_file

    Args:
        input_file: Path to the input file
        output_file: Path to the output file
        preset_config: The preset configuration dict
        preset_name: Name of the preset used
        preset_label: Optional label for the preset (uses preset_config.get('label') if not provided)
    """
    preset_file = input_file.parent / '.preset.json'

    # Read existing preset file if it exists
    if preset_file.exists():
        with open(preset_file, 'r', encoding='utf-8') as f:
            presets = json.load(f)
    else:
        presets = {}

    # Create preset entry
    preset_entry = {
        'preset': preset_name,
        'preset_label': preset_label if preset_label is not None else preset_config.get('label', ''),
        'output_dir': str(output_file).replace('\\', '/'),
    }

    # Add all other preset parameters (mask_r, mask_g, mask_b, contrast, gamma, saturation, etc.)
    for key, value in preset_config.items():
        if key != 'label':  # label already handled as preset_label
            preset_entry[key] = value

    # Update presets with new entry
    presets[input_file.name] = preset_entry

    # Write back to file
    with open(preset_file, 'w', encoding='utf-8') as f:
        json.dump(presets, f, indent=4, ensure_ascii=False)


def get_preset_config(config_path, preset_name="kodak_ultramax_400"):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        preset = config['presets'].get(preset_name)
        if not preset:
            print(f"Error: Preset '{preset_name}' not found in config file")
            return
        return preset
    except Exception as e:
        print(f"Cannot read config file: {e}")
        return


def parse_area(s):
    """Parse '--area' argument 'x1,y1,x2,y2' into a 4-int tuple.

    Strictly requires x2 > x1 and y2 > y1 (degenerate or inverted boxes
    are rejected up-front so we don't push garbage into the white-point
    sampler downstream). Raises ValueError on any malformed input.
    """
    if s is None:
        return None
    parts = [p.strip() for p in s.split(',')]
    if len(parts) != 4:
        raise ValueError(
            f"Invalid --area format. Expected 'x1,y1,x2,y2', got: {s!r}"
        )
    try:
        x1, y1, x2, y2 = (int(p) for p in parts)
    except ValueError:
        raise ValueError(
            f"Invalid --area values. All four coordinates must be integers, got: {s!r}"
        )
    if x2 <= x1 or y2 <= y1:
        raise ValueError(
            f"Invalid --area: must satisfy x2>x1 and y2>y1, got x1={x1}, y1={y1}, x2={x2}, y2={y2}"
        )
    return (x1, y1, x2, y2)


def parse_area_basis(s):
    """Parse '--area-basis' argument 'w,h' into a 2-int tuple.

    Used together with --area to declare what frame those ROI coords were
    measured in (e.g. the resized + rotated working-dir preview the user
    saw). The CLI rescales the ROI to the actual decoded image's frame
    before sampling. Raises ValueError on malformed input.
    """
    if s is None:
        return None
    parts = [p.strip() for p in s.split(',')]
    if len(parts) != 2:
        raise ValueError(
            f"Invalid --area-basis format. Expected 'w,h', got: {s!r}"
        )
    try:
        w, h = (int(p) for p in parts)
    except ValueError:
        raise ValueError(
            f"Invalid --area-basis values. Both must be integers, got: {s!r}"
        )
    if w <= 0 or h <= 0:
        raise ValueError(
            f"Invalid --area-basis: w and h must be positive, got w={w}, h={h}"
        )
    return (w, h)


def parse_white_balance(s):
    """Parse '--white-balance' into the value process_film expects.

    Accepts:
      - 'none'           → 'none'   (no white-balance correction)
      - 'auto'           → 'auto'   (full AWB pulling RGB to neutral)
      - 'x,y' integers in [-50, 50] → (x, y) tuple (AWB then offset)

    Raises ValueError on malformed input.
    """
    if s is None:
        return 'auto'
    s = s.strip()
    if s in ('none', 'auto'):
        return s
    parts = [p.strip() for p in s.split(',')]
    if len(parts) != 2:
        raise ValueError(
            f"Invalid --white-balance: expected 'none', 'auto', or 'x,y', got: {s!r}"
        )
    try:
        x, y = (int(p) for p in parts)
    except ValueError:
        raise ValueError(
            f"Invalid --white-balance values. x and y must be integers, got: {s!r}"
        )
    if not (-50 <= x <= 50 and -50 <= y <= 50):
        raise ValueError(
            f"Invalid --white-balance: x and y must be in [-50, 50], got x={x}, y={y}"
        )
    return (x, y)


def serialize_white_balance(wb):
    """Round-trip the parsed --white-balance value back to its CLI string form
    so it can be persisted in .preset.json and replayed verbatim by SaveAll.
    """
    if isinstance(wb, (list, tuple)):
        return f"{wb[0]},{wb[1]}"
    return wb


def find_config_file():
    """
    Search for configuration file, try in the following order:
    1. config.yaml or config.yml in current working directory
    2. .openlucky/config.yaml or .openlucky/config.yml in user home directory

    Returns:
        Path: Found configuration file path, or None if not found
    """
    # 尝试当前工作目录
    cwd = Path.cwd()
    cwd_config_yaml = cwd / 'config.yaml'
    cwd_config_yml = cwd / 'config.yml'

    if cwd_config_yaml.exists():
        return cwd_config_yaml
    if cwd_config_yml.exists():
        return cwd_config_yml

    # 尝试用户家目录
    home_dir = Path.home()
    home_config_yaml = home_dir / '.openlucky' / 'config.yaml'
    home_config_yml = home_dir / '.openlucky' / 'config.yml'

    if home_config_yaml.exists():
        return home_config_yaml
    if home_config_yml.exists():
        return home_config_yml

    return None


def main():
    parser = argparse.ArgumentParser(description="OpenLucky - Film Negative Processing Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available subcommands')

    # film subcommand
    film_parser = subparsers.add_parser('film', help='Film negative to positive conversion (Kodak UltraMax 400 optimization)')
    film_parser.add_argument('--input', '-i', required=False, help='Input negative film file path (supports .tif, .tiff, .jpg). Leave empty to read from stdin.')
    film_parser.add_argument('--output', '-o', required=False, help='Output file save path. Leave empty to write to stdout.')
    film_parser.add_argument('--config', '-c', required=False, help='Preset configuration file (yaml) path (auto-search if empty)')
    film_parser.add_argument('--preset', '-p', default='kodak_ultramax_400',
                             help='Preset name to use (default: kodak_ultramax_400)')
    film_parser.add_argument('--rotate-clockwise', '-r', type=int, choices=[0, 90, 180, 270], default=0,
                             help='Rotate image clockwise by degrees (0, 90, 180, or 270, default: 0)')
    film_parser.add_argument('--area', '-a', required=False, default=None,
                             help='White-point sampling area in pixels, format "x1,y1,x2,y2" (must satisfy x2>x1 and y2>y1). Leave empty to sample the full image.')
    film_parser.add_argument('--exposure-mode', required=False, default='3ev',
                             choices=['3ev', '5ev', '7ev'],
                             help='Exposure curve mode (default: 3ev)')
    film_parser.add_argument('--exposure', required=False, type=float, default=0.0,
                             help='Exposure compensation in EV (default: 0.0)')
    film_parser.add_argument('--white-balance', '-w', required=False, default='auto',
                             help='White balance mode: "none", "auto", or "x,y" with x=temperature, y=tint, both in [-50, 50] (default: auto)')

    # filmbatch subcommand
    filmbatch_parser = subparsers.add_parser('filmbatch', help='Batch process film negatives')
    filmbatch_parser.add_argument('--input', '-i', required=True, help='Input image directory')
    filmbatch_parser.add_argument('--output', '-o', required=False, help='Output image directory (default: output subdirectory in input directory)')
    filmbatch_parser.add_argument('--config', '-c', required=False, help='Preset configuration file (yaml) path (auto-search if empty)')
    filmbatch_parser.add_argument('--preset', '-p', default='kodak_ultramax_400',
                                   help='Preset name to use (default: kodak_ultramax_400)')
    filmbatch_parser.add_argument('--rotate-clockwise', '-r', type=int, choices=[0, 90, 180, 270], default=0,
                                   help='Rotate image clockwise by degrees (0, 90, 180, or 270, default: 0)')
    filmbatch_parser.add_argument('--area', '-a', required=False, default=None,
                                   help='White-point sampling area in pixels, format "x1,y1,x2,y2" (must satisfy x2>x1 and y2>y1). Leave empty to sample the full image.')
    filmbatch_parser.add_argument('--exposure-mode', required=False, default='3ev',
                                   choices=['3ev', '5ev', '7ev'],
                                   help='Exposure curve mode (default: 3ev)')
    filmbatch_parser.add_argument('--exposure', required=False, type=float, default=0.0,
                                   help='Exposure compensation in EV (default: 0.0)')
    filmbatch_parser.add_argument('--white-balance', '-w', required=False, default='auto',
                                   help='White balance mode: "none", "auto", or "x,y" with x=temperature, y=tint, both in [-50, 50] (default: auto)')

    # filmparam subcommand
    filmparam_parser = subparsers.add_parser('filmparam', help='Film negative to positive conversion with custom parameters')
    filmparam_parser.add_argument('--input', '-i', required=False, help='Input negative film file path (supports .tif, .tiff, .jpg). Leave empty to read from stdin.')
    filmparam_parser.add_argument('--output', '-o', required=False, help='Output file save path. Leave empty to write to stdout.')
    filmparam_parser.add_argument('--param', '-r', required=False,
                                   help='Apply parameters in format "mask_r,mask_g,mask_b,gamma,contrast", e.g., "110,220,210,1.1,1.5"')
    filmparam_parser.add_argument('--rotate-clockwise', '-t', type=int, choices=[0, 90, 180, 270], default=0,
                                   help='Rotate image clockwise by degrees (0, 90, 180, or 270, default: 0)')
    filmparam_parser.add_argument('--area', '-a', required=False, default=None,
                                   help='White-point sampling area in pixels, format "x1,y1,x2,y2" (must satisfy x2>x1 and y2>y1). Leave empty to sample the full image.')
    filmparam_parser.add_argument('--area-basis', '-b', required=False, default=None,
                                   help='Frame dimensions the --area coords were measured in, format "w,h" (the rotated post-resize preview). When set, CLI un-rotates and rescales the ROI to the actual decoded image. Leave empty to interpret --area as actual-image pixels.')
    filmparam_parser.add_argument('--exposure-mode', required=False, default='3ev',
                                   choices=['3ev', '5ev', '7ev'],
                                   help='Exposure curve mode (default: 3ev)')
    filmparam_parser.add_argument('--exposure', required=False, type=float, default=0.0,
                                   help='Exposure compensation in EV (default: 0.0)')
    filmparam_parser.add_argument('--white-balance', '-w', required=False, default='auto',
                                   help='White balance mode: "none", "auto", or "x,y" with x=temperature, y=tint, both in [-50, 50] (default: auto)')

    # filmparambatch subcommand
    filmparambatch_parser = subparsers.add_parser('filmparambatch', help='Batch process film negatives with custom parameters')
    filmparambatch_parser.add_argument('--input', '-i', required=True, help='Input image directory')
    filmparambatch_parser.add_argument('--output', '-o', required=False, help='Output image directory (default: output subdirectory in input directory)')
    filmparambatch_parser.add_argument('--param', '-r', required=True,
                                         help='Apply parameters in format "mask_r,mask_g,mask_b,gamma,contrast", e.g., "110,220,210,1.1,1.5"')
    filmparambatch_parser.add_argument('--rotate-clockwise', '-t', type=int, choices=[0, 90, 180, 270], default=0,
                                         help='Rotate image clockwise by degrees (0, 90, 180, or 270, default: 0)')
    filmparambatch_parser.add_argument('--area', '-a', required=False, default=None,
                                         help='White-point sampling area in pixels, format "x1,y1,x2,y2" (must satisfy x2>x1 and y2>y1). Leave empty to sample the full image.')
    filmparambatch_parser.add_argument('--area-basis', '-b', required=False, default=None,
                                         help='Frame dimensions the --area coords were measured in, format "w,h" (the rotated post-resize preview). When set, CLI un-rotates and rescales the ROI to the actual decoded image. Leave empty to interpret --area as actual-image pixels.')
    filmparambatch_parser.add_argument('--exposure-mode', required=False, default='3ev',
                                         choices=['3ev', '5ev', '7ev'],
                                         help='Exposure curve mode (default: 3ev)')
    filmparambatch_parser.add_argument('--exposure', required=False, type=float, default=0.0,
                                         help='Exposure compensation in EV (default: 0.0)')
    filmparambatch_parser.add_argument('--white-balance', '-w', required=False, default='auto',
                                         help='White balance mode: "none", "auto", or "x,y" with x=temperature, y=tint, both in [-50, 50] (default: auto)')

    # raw2tiff subcommand
    raw2tiff_parser = subparsers.add_parser('raw2tiff', help='RAW to TIFF format conversion')
    raw2tiff_parser.add_argument('--input', '-i', required=True, help='Input RAW file path')
    raw2tiff_parser.add_argument('--output', '-o', required=True, help='Output TIFF file path')

    # tiff2jpeg subcommand
    tiff_parser = subparsers.add_parser('tiff2jpeg', help='TIFF to JPEG format conversion')
    tiff_parser.add_argument('--input', '-i', required=True, help='Input TIFF file path')
    tiff_parser.add_argument('--output', '-o', required=True, help='Output JPEG file path')

    # config subcommand
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_subparsers = config_parser.add_subparsers(dest='config_command', help='Available config subcommands')

    # config read subcommand
    config_read_parser = config_subparsers.add_parser('read', help='Read configuration file')
    config_read_parser.add_argument('--config', '-c', required=False, help='Configuration file (yaml) path (auto-search if empty)')
    config_read_parser.add_argument('--format', '-f', default='yaml', choices=['json', 'yaml'], help='Output format (default: yaml)')

    # tool subcommand
    tool_parser = subparsers.add_parser('tool', help='Image processing tools')
    tool_subparsers = tool_parser.add_subparsers(dest='tool_command', help='Available tool subcommands')

    # tool resize subcommand
    resize_parser = tool_subparsers.add_parser('resize', help='Resize images')
    resize_parser.add_argument('--input', '-i', required=True, help='Input image file path')
    resize_parser.add_argument('--output', '-o', required=True, help='Output image file path')
    resize_parser.add_argument('--edge', '-e', default='long-edge',
                               choices=['width', 'height', 'long-edge', 'short-edge'],
                               help='Edge to use as resize basis (default: long-edge)')
    resize_parser.add_argument('--mode', '-m', default='fixed-value',
                               choices=['ratio', 'fixed-value'],
                               help='Resize mode: ratio (0-1) or fixed-value (positive integer) (default: fixed-value)')
    resize_parser.add_argument('--value', '-v', required=False, default=None,
                               help='Resize value: ratio (0-1 float) or fixed-value (positive integer). '
                                    'If not provided, no resize is performed (non-RAW copied directly, RAW converted to TIFF).')

    # tool pick subcommand
    pick_parser = tool_subparsers.add_parser('pick', help='Pick a single pixel color (JSON output to stdout)')
    pick_parser.add_argument('--input', '-i', required=True, help='Input image file path')
    pick_parser.add_argument('--x', '-x', type=int, required=True, help='X pixel coordinate (0-indexed)')
    pick_parser.add_argument('--y', '-y', type=int, required=True, help='Y pixel coordinate (0-indexed)')
    pick_parser.add_argument('--format', '-f', default='8',
                             choices=['8', '16'],
                             help='Output bit depth (default: 8)')

    # tool histogram subcommand
    histogram_parser = tool_subparsers.add_parser('histogram', help='Compute image histogram (JSON output to stdout)')
    histogram_parser.add_argument('--input', '-i', required=True, help='Input image file path')
    histogram_parser.add_argument('--type', '-t', default='rgbl',
                                  choices=['rgbl'],
                                  help='Histogram type. rgbl = R/G/B/luminance (BT.601). Default: rgbl')
    histogram_parser.add_argument('--gamma', '-g', type=float, default=1.0,
                                  help='Gamma applied before histogramming (default: 1.0; suggest 2.2 for RAW)')
    histogram_parser.add_argument('--mode', '-m', default='log',
                                  choices=['log', 'linear'],
                                  help='Per-bin transform applied to counts (default: log). The renderer scales data by visual_meta.suggested_max_y.')
    histogram_parser.add_argument('--downsampling', '-d', type=int, default=None,
                                  help='X-axis bin count after downsampling. Power of 2 in [256, 65536]. Leave unset to keep native bit depth.')
    histogram_parser.add_argument('--area', '-a', required=False, default=None,
                                  help='Restrict histogram to pixels inside this rectangle, format "x1,y1,x2,y2" (must satisfy x2>x1 and y2>y1). Leave empty to use the whole image.')

    # tool reshape subcommand
    reshape_parser = tool_subparsers.add_parser('reshape', help='Four-point perspective correction')
    reshape_parser.add_argument('--input', '-i', required=True, help='Input image file path')
    reshape_parser.add_argument('--output', '-o', required=True, help='Output image file path')
    reshape_parser.add_argument('--point1', '-p1', required=True, help='Top-left crop anchor point (x,y format, e.g., 10,13)')
    reshape_parser.add_argument('--point2', '-p2', required=True, help='Top-right crop anchor point (x,y format, e.g., 100,14)')
    reshape_parser.add_argument('--point3', '-p3', required=True, help='Bottom-right crop anchor point (x,y format, e.g., 101,134)')
    reshape_parser.add_argument('--point4', '-p4', required=True, help='Bottom-left crop anchor point (x,y format, e.g., 8,132)')
    reshape_parser.add_argument('--shape', '-s', required=True, help='Output canvas dimensions (width,height format, e.g., 6000,4000)')

    # curve subcommand
    curve_parser = subparsers.add_parser('curve', help='Curve adjustment tools')
    curve_subparsers = curve_parser.add_subparsers(dest='curve_command', help='Available curve subcommands')

    # curve levels subcommand
    levels_parser = curve_subparsers.add_parser('levels', help='Highlight and shadow clipping')
    levels_parser.add_argument('--shadows', '-s', type=int, default=0,
                               help='Shadow clipping in permilles (0-1000)')
    levels_parser.add_argument('--highlights', '-hl', type=int, default=0,
                               help='Highlight clipping in permilles (0-1000)')
    levels_parser.add_argument('--channel', '-c', default='all',
                               choices=['all', 'red', 'green', 'blue'],
                               help='Channel to apply clipping (default: all)')
    levels_parser.add_argument('--mode', '-m', default='clip-stretch',
                               choices=['clip-only', 'clip-stretch'],
                               help='Clipping mode (default: clip-stretch)')
    levels_parser.add_argument('--input', '-i', required=True, help='Input image file path')
    levels_parser.add_argument('--output', '-o', required=True, help='Output image file path')

    args = parser.parse_args()

    if args.command == 'film':
        # Validate optional ROI early so we fail before doing any I/O.
        try:
            roi = parse_area(args.area)
            white_balance = parse_white_balance(args.white_balance)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Read input from file or stdin
        if args.input is not None:
            input_file = Path(args.input)
            if not input_file.exists():
                print(f"Error: Input file does not exist: {input_file}")
                sys.exit(1)

            try:
                with open(input_file, 'rb') as f:
                    input_bytes = f.read()
            except Exception as e:
                print(f"Error: Cannot read input file '{input_file}': {e}")
                sys.exit(1)
        else:
            try:
                input_bytes = sys.stdin.buffer.read()
            except Exception as e:
                print(f"Error: Failed to read from stdin: {e}", file=sys.stderr)
                sys.exit(1)

        # If no config file specified, auto-search
        if args.config is None:
            print("No config file specified, auto-searching...")
            config_file = find_config_file()
            if config_file is None:
                print("Error: Configuration file not found. Please create config.yaml or config.yml in one of the following locations:")
                print("  1. Current working directory")
                print("  2. .openlucky directory in user home directory (e.g. C:\\Users\\YourName\\.openlucky)")
                sys.exit(1)
            print(f"Found config file: {config_file}")
        else:
            config_file = Path(args.config)

        if not config_file.exists():
            print(f"Error: Configuration file does not exist: {config_file}")
            sys.exit(1)

        # Process with byte stream function
        preset = get_preset_config(config_file, args.preset)

        # Check if input file is RAW format (do it once when we have file info)
        if args.input is not None:
            ext = input_file.suffix.lower()
            is_raw = ext in RAW_EXTENSIONS
        else:
            # For stdin input, cannot determine if it's RAW from extension, default to False
            is_raw = False

        output_bytes = process_film_bytestream_with_params(
            input_bytes,
            preset_mask_b=preset['mask_b'],
            preset_mask_g=preset['mask_g'],
            preset_mask_r=preset['mask_r'],
            preset_contrast_r=preset.get('contrast_r', 1.0),
            preset_contrast_g=preset.get('contrast_g', 1.0),
            preset_contrast_b=preset.get('contrast_b', 1.0),
            preset_gamma=preset.get('gamma', 1.0),
            preset_contrast=preset.get('contrast', 1.0),
            rotate_clockwise=args.rotate_clockwise,
            wp_roi_x1=roi[0] if roi else None,
            wp_roi_y1=roi[1] if roi else None,
            wp_roi_x2=roi[2] if roi else None,
            wp_roi_y2=roi[3] if roi else None,
            exposure_ev_mode=args.exposure_mode,
            exposure_ev=args.exposure,
            white_balance=white_balance,
            is_raw=is_raw
        )

        if output_bytes is None:
            print("Error: Failed to process image", file=sys.stderr)
            sys.exit(1)

        # Write output to file or stdout
        if args.output is not None:
            output_file = Path(args.output)
            try:
                with open(output_file, 'wb') as f:
                    f.write(output_bytes)
                print(f"Successfully saved to: {output_file}")
            except Exception as e:
                print(f"Error: Cannot write output file '{output_file}': {e}")
                sys.exit(1)
        else:
            sys.stdout.buffer.write(output_bytes)

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config:
                # Save preset to .preset.json
                preset_config = config['presets'].get(args.preset)
                if preset_config:
                    # Add rotate_clockwise to preset_config
                    preset_config['rotate_clockwise'] = args.rotate_clockwise
                    preset_config['white_balance'] = serialize_white_balance(white_balance)
                    # Use forward slashes in path to avoid double backslashes in JSON
                    if args.output is not None:
                        output_path_for_preset = Path(args.output)
                    else:
                        output_path_for_preset = None
                    save_preset_to_json(Path(args.input) if args.input else None, output_path_for_preset, preset_config, args.preset, preset_config.get('label'))

    elif args.command == 'filmbatch':
        # Validate optional ROI early so we fail before walking the directory.
        try:
            roi = parse_area(args.area)
            white_balance = parse_white_balance(args.white_balance)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        input_dir = Path(args.input)
        output_dir = Path(args.output) if args.output else input_dir / 'output'

        # Verify input directory
        if not input_dir.exists():
            print(f"Error: Input directory does not exist: {input_dir}")
            sys.exit(1)
        if not input_dir.is_dir():
            print(f"Error: Input path is not a directory: {input_dir}")
            sys.exit(1)

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        # Find config file
        if args.config is None:
            print("No config file specified, auto-searching...")
            config_file = find_config_file()
            if config_file is None:
                print("Error: Configuration file not found. Please create config.yaml or config.yml in one of the following locations:")
                print("  1. Current working directory")
                print("  2. .openlucky directory in user home directory (e.g. C:\\Users\\YourName\\.openlucky)")
                sys.exit(1)
            print(f"Found config file: {config_file}")
        else:
            config_file = Path(args.config)

        if not config_file.exists():
            print(f"Error: Configuration file does not exist: {config_file}")
            sys.exit(1)

        # Search for images in input directory
        image_files = []
        for ext in IMAGE_EXTENSIONS:
            image_files.extend(input_dir.glob(f'*{ext}'))
            image_files.extend(input_dir.glob(f'*{ext.upper()}'))

        if not image_files:
            print(f"Warning: No supported image files found in {input_dir}")
            print(f"Supported formats: {', '.join(IMAGE_EXTENSIONS)}")
            sys.exit(0)

        print(f"Found {len(image_files)} image files")

        # Load preset config once for all files
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        preset_config = config['presets'].get(args.preset)
        if not preset_config:
            print(f"Error: Preset '{args.preset}' not found in config file")
            sys.exit(1)

        # Batch processing - collect presets first
        success_count = 0
        fail_count = 0
        presets_by_dir = {}  # Group presets by input directory

        for i, input_file in enumerate(image_files, 1):
            print(f"[{i}/{len(image_files)}] Processing negative: {input_file.name}")
            try:
                output_file = output_dir / input_file.name
                success_count += 1
                
                preset = get_preset_config(config_file, args.preset)
   
                process_film_with_params(
                    input_file,
                    output_file,
                    preset_mask_b=preset['mask_b'],
                    preset_mask_g=preset['mask_g'],
                    preset_mask_r=preset['mask_r'],
                    preset_contrast_r=preset.get('contrast_r', 1.0),
                    preset_contrast_g=preset.get('contrast_g', 1.0),
                    preset_contrast_b=preset.get('contrast_b', 1.0),
                    preset_gamma=preset.get('gamma', 1.0),
                    preset_contrast=preset.get('contrast', 1.0),
                    rotate_clockwise=args.rotate_clockwise,
                    wp_roi_x1=roi[0] if roi else None,
                    wp_roi_y1=roi[1] if roi else None,
                    wp_roi_x2=roi[2] if roi else None,
                    wp_roi_y2=roi[3] if roi else None,
                    exposure_ev_mode=args.exposure_mode,
                    exposure_ev=args.exposure,
                    white_balance=white_balance,
                )


                # Collect preset info for later batch write
                dir_key = str(input_file.parent)
                if dir_key not in presets_by_dir:
                    presets_by_dir[dir_key] = {}
                presets_by_dir[dir_key][input_file.name] = {
                    'preset': args.preset,
                    'preset_label': preset_config.get('label', ''),
                    'output_dir': str(output_file).replace('\\', '/'),
                }
                # Add all other preset parameters
                for key, value in preset_config.items():
                    if key != 'label':
                        presets_by_dir[dir_key][input_file.name][key] = value
                # Add rotate_clockwise
                presets_by_dir[dir_key][input_file.name]['rotate_clockwise'] = args.rotate_clockwise
                presets_by_dir[dir_key][input_file.name]['white_balance'] = serialize_white_balance(white_balance)
            except Exception as e:
                print(e)
                fail_count += 1

        # Batch write all presets to .preset.json files
        for dir_path, presets in presets_by_dir.items():
            preset_file = Path(dir_path) / '.preset.json'

            # Read existing preset file if it exists
            existing_presets = {}
            if preset_file.exists():
                with open(preset_file, 'r', encoding='utf-8') as f:
                    existing_presets = json.load(f)

            # Merge with new presets
            existing_presets.update(presets)

            # Write back to file
            with open(preset_file, 'w', encoding='utf-8') as f:
                json.dump(existing_presets, f, indent=4, ensure_ascii=False)
            print(f"Saved {len(presets)} preset(s) to {preset_file}")

    elif args.command == 'filmparam':
        # Validate optional ROI early so we fail before doing any I/O.
        try:
            roi = parse_area(args.area)
            area_basis = parse_area_basis(args.area_basis)
            white_balance = parse_white_balance(args.white_balance)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Parse parameters
        if args.param is None:
            print("Error: --param is required for filmparam command")
            sys.exit(1)

        try:
            params = args.param.split(',')
            contrast_r = 1
            contrast_g = 1
            contrast_b = 1
            if len(params) < 5:
                print(f"Error: Invalid parameter format. Expected 'mask_r,mask_g,mask_b,gamma,contrast', got: {args.param}")
                sys.exit(1)
            elif len(params) == 8:
                # Support extended format with contrast_r, contrast_g, contrast_b
                contrast_r = float(params[5])
                contrast_g = float(params[6])
                contrast_b = float(params[7])
            mask_r = float(params[0])
            mask_g = float(params[1])
            mask_b = float(params[2])
            gamma = float(params[3])
            contrast = float(params[4])
        except ValueError as e:
            print(f"Error: Failed to parse parameters: {e}")
            print("Expected format: 'mask_r,mask_g,mask_b,gamma,contrast', e.g., '110,220,210,1.1,1.5'")
            sys.exit(1)

        is_raw = False
        # Read input from file or stdin
        if args.input is not None:
            input_file = Path(args.input)

            ext = input_file.suffix.lower()
            is_raw = ext in RAW_EXTENSIONS
            
            if not input_file.exists():
                print(f"Error: Input file does not exist: {input_file}")
                sys.exit(1)

            try:
                with open(input_file, 'rb') as f:
                    input_bytes = f.read()
            except Exception as e:
                print(f"Error: Cannot read input file '{input_file}': {e}")
                sys.exit(1)
        else:
            try:
                input_bytes = sys.stdin.buffer.read()
            except Exception as e:
                print(f"Error: Failed to read from stdin: {e}", file=sys.stderr)
                sys.exit(1)

        # Process with byte stream function
        output_bytes = process_film_bytestream_with_params(
            input_bytes,
            preset_mask_r=mask_r,
            preset_mask_g=mask_g,
            preset_mask_b=mask_b,
            preset_contrast_r=contrast_r,
            preset_contrast_g=contrast_g,
            preset_contrast_b=contrast_b,
            preset_gamma=gamma,
            preset_contrast=contrast,
            rotate_clockwise=args.rotate_clockwise,
            wp_roi_x1=roi[0] if roi else None,
            wp_roi_y1=roi[1] if roi else None,
            wp_roi_x2=roi[2] if roi else None,
            wp_roi_y2=roi[3] if roi else None,
            area_basis_w=area_basis[0] if area_basis else None,
            area_basis_h=area_basis[1] if area_basis else None,
            exposure_ev_mode=args.exposure_mode,
            exposure_ev=args.exposure,
            white_balance=white_balance,
            is_raw=is_raw
        )

        if output_bytes is None:
            print("Error: Failed to process image", file=sys.stderr)
            sys.exit(1)

        # Write output to file or stdout
        if args.output is not None:
            output_file = Path(args.output)
            try:
                with open(output_file, 'wb') as f:
                    f.write(output_bytes)
                print(f"Successfully saved to: {output_file}")
            except Exception as e:
                print(f"Error: Cannot write output file '{output_file}': {e}")
                sys.exit(1)
        else:
            sys.stdout.buffer.write(output_bytes)

        # Save preset to .preset.json
        preset_name = f"custom_preset_{int(time.time())}"
        preset_label = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        preset_config = {
            'mask_r': mask_r,
            'mask_g': mask_g,
            'mask_b': mask_b,
            "contrast_r": contrast_r,
            "contrast_g": contrast_g,
            "contrast_b": contrast_b,
            'gamma': gamma,
            'contrast': contrast,
            'rotate_clockwise': args.rotate_clockwise,
            'exposure_ev_mode': args.exposure_mode,
            'exposure_ev': args.exposure,
            'white_balance': serialize_white_balance(white_balance),
        }
        # Persist white-point ROI + basis so a later batch save against the
        # original full-res file can replay the same sampling window.
        if roi is not None:
            preset_config['area'] = {
                'x1': roi[0], 'y1': roi[1], 'x2': roi[2], 'y2': roi[3],
            }
            if area_basis is not None:
                preset_config['area_basis'] = {
                    'w': area_basis[0], 'h': area_basis[1],
                }
        input_path_for_preset = Path(args.input) if args.input else None
        output_path_for_preset = Path(args.output) if args.output else None
        save_preset_to_json(input_path_for_preset, output_path_for_preset, preset_config, preset_name, preset_label)

    elif args.command == 'filmparambatch':
        # Validate optional ROI early so we fail before walking the directory.
        try:
            roi = parse_area(args.area)
            area_basis = parse_area_basis(args.area_basis)
            white_balance = parse_white_balance(args.white_balance)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        input_dir = Path(args.input)
        output_dir = Path(args.output) if args.output else input_dir / 'output'

        # Parse parameters
        try:
            params = args.param.split(',')
            contrast_r = 1
            contrast_g = 1
            contrast_b = 1
            if len(params) < 5:
                print(f"Error: Invalid parameter format. Expected 'mask_r,mask_g,mask_b,gamma,contrast', got: {args.param}")
                sys.exit(1)
            elif len(params) == 8:
                # Support extended format with contrast_r, contrast_g, contrast_b
                contrast_r = float(params[5])
                contrast_g = float(params[6])
                contrast_b = float(params[7])
            mask_r = float(params[0])
            mask_g = float(params[1])
            mask_b = float(params[2])
            gamma = float(params[3])
            contrast = float(params[4])
        except ValueError as e:
            print(f"Error: Failed to parse parameters: {e}")
            print("Expected format: 'mask_r,mask_g,mask_b,gamma,contrast', e.g., '110,220,210,1.1,1.5'")
            sys.exit(1)

        # Verify input directory
        if not input_dir.exists():
            print(f"Error: Input directory does not exist: {input_dir}")
            sys.exit(1)
        if not input_dir.is_dir():
            print(f"Error: Input path is not a directory: {input_dir}")
            sys.exit(1)

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory: {output_dir}")

        # Search for images in input directory
        image_files = []
        for ext in IMAGE_EXTENSIONS:
            image_files.extend(input_dir.glob(f'*{ext}'))
            image_files.extend(input_dir.glob(f'*{ext.upper()}'))

        if not image_files:
            print(f"Warning: No supported image files found in {input_dir}")
            print(f"Supported formats: {', '.join(IMAGE_EXTENSIONS)}")
            sys.exit(0)

        print(f"Found {len(image_files)} image files")

        # Generate preset name and label once for all files
        preset_name = f"custom_preset_{int(time.time())}"
        preset_label = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        preset_config = {
            'mask_r': mask_r,
            'mask_g': mask_g,
            'mask_b': mask_b,
            "contrast_r": contrast_r,
            "contrast_g": contrast_g,
            "contrast_b": contrast_b,
            'gamma': gamma,
            'contrast': contrast,
            'rotate_clockwise': args.rotate_clockwise,
            'exposure_ev_mode': args.exposure_mode,
            'exposure_ev': args.exposure,
            'white_balance': serialize_white_balance(white_balance),
        }
        # Persist ROI + basis alongside the per-file preset so a later
        # batch save against the original full-res file can replay sampling.
        if roi is not None:
            preset_config['area'] = {
                'x1': roi[0], 'y1': roi[1], 'x2': roi[2], 'y2': roi[3],
            }
            if area_basis is not None:
                preset_config['area_basis'] = {
                    'w': area_basis[0], 'h': area_basis[1],
                }

        # Batch processing - collect presets first
        success_count = 0
        fail_count = 0
        presets_by_dir = {}  # Group presets by input directory

        for i, input_file in enumerate(image_files, 1):
            print(f"[{i}/{len(image_files)}] Processing negative: {input_file.name}")
            try:
                output_file = output_dir / input_file.name
                process_film_with_params(
                    input_file,
                    output_file,
                    preset_mask_b=mask_b,
                    preset_mask_g=mask_g,
                    preset_mask_r=mask_r,
                    preset_contrast_r=contrast_r,
                    preset_contrast_g=contrast_g,
                    preset_contrast_b=contrast_b,
                    preset_gamma=gamma,
                    preset_contrast=contrast,
                    rotate_clockwise=args.rotate_clockwise,
                    wp_roi_x1=roi[0] if roi else None,
                    wp_roi_y1=roi[1] if roi else None,
                    wp_roi_x2=roi[2] if roi else None,
                    wp_roi_y2=roi[3] if roi else None,
                    area_basis_w=area_basis[0] if area_basis else None,
                    area_basis_h=area_basis[1] if area_basis else None,
                    exposure_ev_mode=args.exposure_mode,
                    exposure_ev=args.exposure,
                    white_balance=white_balance,
                )
                success_count += 1

                # Collect preset info for later batch write
                dir_key = str(input_file.parent)
                if dir_key not in presets_by_dir:
                    presets_by_dir[dir_key] = {}
                presets_by_dir[dir_key][input_file.name] = {
                    'preset': preset_name,
                    'preset_label': preset_label,
                    'output_dir': str(output_file).replace('\\', '/'),
                }
                # Add all other preset parameters
                for key, value in preset_config.items():
                    presets_by_dir[dir_key][input_file.name][key] = value
            except Exception as e:
                print(f"Error processing {input_file.name}: {e}")
                fail_count += 1

        # Batch write all presets to .preset.json files
        for dir_path, presets in presets_by_dir.items():
            preset_file = Path(dir_path) / '.preset.json'

            # Read existing preset file if it exists
            existing_presets = {}
            if preset_file.exists():
                with open(preset_file, 'r', encoding='utf-8') as f:
                    existing_presets = json.load(f)

            # Merge with new presets
            existing_presets.update(presets)

            # Write back to file
            with open(preset_file, 'w', encoding='utf-8') as f:
                json.dump(existing_presets, f, indent=4, ensure_ascii=False)
            print(f"Saved {len(presets)} preset(s) to {preset_file}")

        print(f"\nBatch processing complete: {success_count} succeeded, {fail_count} failed")

    elif args.command == 'raw2tiff':
        raw_to_tiff(args.input, args.output)

    elif args.command == 'tiff2jpeg':
        convert_tiff_to_jpeg(args.input, args.output)

    elif args.command == 'config':
        if args.config_command == 'read':
            # Find config file
            if args.config is None:
                config_file = find_config_file()
                if config_file is None:
                    print("Error: Configuration file not found. Please create config.yaml or config.yml in one of the following locations:")
                    print("  1. Current working directory")
                    print("  2. .openlucky directory in user home directory (e.g. C:\\Users\\YourName\\.openlucky)")
                    sys.exit(1)
            else:
                config_file = Path(args.config)

            if not config_file.exists():
                print(f"Error: Configuration file does not exist: {config_file}")
                sys.exit(1)

            # Read YAML file
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_content = f.read()
            except Exception as e:
                print(f"Error: Failed to read config file: {e}")
                sys.exit(1)

            # Output in specified format
            if args.format == 'json':
                try:
                    parsed_config = yaml.safe_load(config_content)
                    print(json.dumps(parsed_config, indent=2, ensure_ascii=False))
                except Exception as e:
                    print(f"Error: Failed to parse config as JSON: {e}")
                    sys.exit(1)
            else:  # yaml - output original draft directly
                print(config_content)
        else:
            config_parser.print_help()
            sys.exit(1)

    elif args.command == 'tool':
        if args.tool_command == 'resize':
            # Parse value based on mode (only if --value is provided)
            value = None
            if args.value is not None:
                if args.mode == 'ratio':
                    try:
                        value = float(args.value)
                    except ValueError:
                        print(f"Error: Invalid value for ratio mode. Expected float in (0, 1], got '{args.value}'")
                        sys.exit(1)
                elif args.mode == 'fixed-value':
                    try:
                        value = int(args.value)
                    except ValueError:
                        print(f"Error: Invalid value for fixed-value mode. Expected positive integer, got '{args.value}'")
                        sys.exit(1)

            # Perform resize
            success = resize_image(
                input_path=args.input,
                output_path=args.output,
                edge=args.edge,
                mode=args.mode,
                value=value
            )

            if not success:
                sys.exit(1)
        elif args.tool_command == 'reshape':
            # Parse points
            try:
                point1 = parse_point(args.point1, 'point1')
                point2 = parse_point(args.point2, 'point2')
                point3 = parse_point(args.point3, 'point3')
                point4 = parse_point(args.point4, 'point4')
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)

            # Parse shape
            try:
                shape = parse_shape(args.shape)
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)

            # Perform reshape
            success = reshape_image(
                input_path=args.input,
                output_path=args.output,
                point1=point1,
                point2=point2,
                point3=point3,
                point4=point4,
                shape=shape
            )

            if not success:
                sys.exit(1)
        elif args.tool_command == 'pick':
            try:
                result = pick_color(
                    input_path=args.input,
                    x=args.x,
                    y=args.y,
                    output_format=args.format,
                )
            except (FileNotFoundError, ValueError) as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

            sys.stdout.write(json.dumps(result))
            sys.stdout.write("\n")
        elif args.tool_command == 'histogram':
            try:
                hist_area = parse_area(args.area)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
            try:
                hist = compute_histogram(
                    input_path=args.input,
                    hist_type=args.type,
                    gamma=args.gamma,
                    mode=args.mode,
                    downsampling=args.downsampling,
                    area=hist_area,
                )
            except (FileNotFoundError, ValueError) as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

            sys.stdout.write(json.dumps(hist))
            sys.stdout.write("\n")
        else:
            tool_parser.print_help()
            sys.exit(1)

    elif args.command == 'curve':
        if args.curve_command == 'levels':
            input_file = Path(args.input)
            if not input_file.exists():
                print(f"Error: Input file does not exist: {input_file}")
                sys.exit(1)

            output_file = Path(args.output)

            # For RAW input, ensure output has .tiff extension
            ext = input_file.suffix.lower()
            if ext in RAW_EXTENSIONS and output_file.suffix.lower() not in ('.tif', '.tiff'):
                output_file = output_file.with_suffix(output_file.suffix + '.tiff')
                print(f"RAW input detected, output will be saved as TIFF: {output_file}")

            success = levels_clip(
                input_path=input_file,
                output_path=output_file,
                shadows=args.shadows,
                highlights=args.highlights,
                channel=args.channel,
                mode=args.mode,
            )

            if not success:
                sys.exit(1)
        else:
            curve_parser.print_help()
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
