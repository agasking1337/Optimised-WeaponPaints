import argparse
from concurrent.futures import ProcessPoolExecutor
import os
from pathlib import Path

from PIL import Image


def _convert_one(args):
    png_str, webp_str, quality, overwrite = args
    png_path = Path(png_str)
    webp_path = Path(webp_str)

    if not overwrite and webp_path.exists():
        return True, f"Skipping existing: {webp_path}"

    try:
        webp_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(png_path) as img:
            img.save(webp_path, "WEBP", quality=quality)
        return True, f"Converted: {png_path} -> {webp_path}"
    except Exception as exc:
        return False, f"Failed to convert {png_path}: {exc}"


def convert_png_to_webp(root: Path, output_root: Path, quality: int = 80, overwrite: bool = False, workers: int = 0) -> None:
    png_files = list(root.rglob("*.png"))
    total = len(png_files)
    print(f"Found {total} PNG files under {root}")

    if not png_files:
        return

    if workers <= 0:
        workers = os.cpu_count() or 1

    print(f"Using {workers} worker(s)")

    output_root.mkdir(parents=True, exist_ok=True)
    base_in_output = output_root / root.name

    tasks = []
    for p in png_files:
        rel = p.relative_to(root)
        webp_path = (base_in_output / rel).with_suffix(".webp")
        tasks.append((str(p), str(webp_path), quality, overwrite))

    with ProcessPoolExecutor(max_workers=workers) as executor:
        for idx, (ok, msg) in enumerate(executor.map(_convert_one, tasks), 1):
            print(f"[{idx}/{total}] {msg}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert all PNG files in a folder (recursively) to WebP, keeping the same base name.",
    )
    parser.add_argument(
        "--root",
        type=str,
        default="skins",
        help="Folder to scan for PNG files (default: skins)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=100,
        help="WEBP quality (0-100, default: 80)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .webp files if they already exist.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="img",
        help="Root folder where converted images will be written (default: img)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Number of parallel workers to use (0 = auto, default: 0)",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    root_arg = Path(args.root)
    if not root_arg.is_absolute():
        root_path = project_root / root_arg
    else:
        root_path = root_arg

    if not root_path.exists():
        print(f"Root folder does not exist: {root_path}")
        return

    output_arg = Path(args.output_root)
    if not output_arg.is_absolute():
        output_root = project_root / output_arg
    else:
        output_root = output_arg

    convert_png_to_webp(
        root_path,
        output_root=output_root,
        quality=args.quality,
        overwrite=args.overwrite,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
