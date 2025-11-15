import argparse
import json
from pathlib import Path

OLD_BASE = "https://raw.githubusercontent.com/Nereziel/cs2-WeaponPaints/main/website/img/"
NEW_BASE = "https://raw.githubusercontent.com/agasking1337/Optimised-WeaponPaints/master/img/"


def convert_url(url: str) -> str:
    if not isinstance(url, str):
        return url

    if not url.startswith(OLD_BASE):
        return url

    rel = url[len(OLD_BASE) :]

    if rel.endswith(".png"):
        rel = rel[: -len(".png")] + ".webp"

    return NEW_BASE + rel


def process_json_file(path: Path) -> int:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    changed = 0

    def update_obj(obj):
        nonlocal changed
        if isinstance(obj, dict):
            if "image" in obj:
                old = obj["image"]
                new = convert_url(old)
                if new != old:
                    obj["image"] = new
                    changed += 1
            for v in obj.values():
                update_obj(v)
        elif isinstance(obj, list):
            for item in obj:
                update_obj(item)

    update_obj(data)

    if changed:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Update image URLs in JSON files from the original cs2-WeaponPaints repo "
            "(PNG under website/img) to the new Optimised-WeaponPaints repo (WebP under img)."
        ),
    )
    parser.add_argument(
        "--data-root",
        type=str,
        default="data",
        help="Folder containing JSON data files (default: data)",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    data_root = project_root / args.data_root

    if not data_root.exists():
        print(f"Data folder does not exist: {data_root}")
        return

    json_files = sorted(data_root.glob("*.json"))
    print(f"Found {len(json_files)} JSON files in {data_root}")

    total_changed = 0
    for jf in json_files:
        changed = process_json_file(jf)
        total_changed += changed
        print(f"{jf.name}: updated {changed} image URL(s)")

    print(f"Total updated image URLs: {total_changed}")


if __name__ == "__main__":
    main()
