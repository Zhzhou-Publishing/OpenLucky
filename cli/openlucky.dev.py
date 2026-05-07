import argparse
import numpy as np
import os
from itertools import product

from cli.lib.curve.s_curve import power_curve_raw


FUNC_REGISTRY = {"s-curve.power-curve": power_curve_raw}


def generate_lut(func_name, arg_names, mins, maxs, steps, output_dir):
    if func_name not in FUNC_REGISTRY:
        print(f"Error: Function '{func_name}' not found.")
        return

    target_func = FUNC_REGISTRY[func_name]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 核心修改：为每个参数应用其专属的步长
    ranges = [np.arange(m, ma + s / 10, s) for m, ma, s in zip(mins, maxs, steps)]
    combinations = list(product(*ranges))

    print(f"Generating {len(combinations)} LUTs...")

    for combo in combinations:
        params = dict(zip(arg_names, combo))
        x = np.linspace(0, 1, 65536)
        lut_data = target_func(x, **params)
        lut_u16 = (np.clip(lut_data, 0, 1) * 65535).astype(np.uint16)

        param_parts = [f"{n}-{f'{v:.2f}'.replace('.', '_')}" for n, v in params.items()]
        filename = (
            f"com.github.zhzhou-publishing.openlucky.s-curve.{func_name}-"
            + "-".join(param_parts)
            + ".lut"
        )

        lut_u16.tofile(os.path.join(output_dir, filename))

    print(f"Success! Saved to '{output_dir}'.")


def main():
    parser = argparse.ArgumentParser(description="OpenLucky Dev Tools")
    subparsers = parser.add_subparsers(dest="command")
    gen_parser = subparsers.add_parser("genlut")

    gen_parser.add_argument("--func", type=str, required=True)
    gen_parser.add_argument("--arg", type=str, required=True, help="e.g., p,k")
    gen_parser.add_argument("--min", type=str, required=True, help="e.g., 0.3,0.5")
    gen_parser.add_argument("--max", type=str, required=True, help="e.g., 0.7,2.5")
    gen_parser.add_argument("--step", type=str, required=True, help="e.g., 0.1,0.05")
    gen_parser.add_argument("--output", type=str, default="lut")

    args = parser.parse_args()

    if args.command == "genlut":
        arg_names = args.arg.split(",")
        mins = [float(x) for x in args.min.split(",")]
        maxs = [float(x) for x in args.max.split(",")]
        steps = [float(x) for x in args.step.split(",")]

        if not (len(arg_names) == len(mins) == len(maxs) == len(steps)):
            print("Error: Arg, Min, Max, and Step counts must match.")
            return

        generate_lut(args.func, arg_names, mins, maxs, steps, args.output)


if __name__ == "__main__":
    main()
