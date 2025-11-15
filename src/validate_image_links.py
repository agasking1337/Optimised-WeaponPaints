import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


def collect_image_urls_from_obj(obj, filename: str, url_to_files: Dict[str, Set[str]]) -> None:
    if isinstance(obj, dict):
        if "image" in obj and isinstance(obj["image"], str) and obj["image"].startswith("http"):
            url = obj["image"]
            url_to_files.setdefault(url, set()).add(filename)
        for v in obj.values():
            collect_image_urls_from_obj(v, filename, url_to_files)
    elif isinstance(obj, list):
        for item in obj:
            collect_image_urls_from_obj(item, filename, url_to_files)


def collect_image_urls(data_root: Path) -> Dict[str, Set[str]]:
    url_to_files: Dict[str, Set[str]] = {}

    json_files = sorted(data_root.glob("*.json"))
    print(f"Found {len(json_files)} JSON files in {data_root}")

    for jf in json_files:
        try:
            with jf.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"Failed to read JSON from {jf}: {exc}")
            continue

        collect_image_urls_from_obj(data, jf.name, url_to_files)

    print(f"Collected {len(url_to_files)} unique image URL(s)")
    return url_to_files


def check_url(url: str, timeout: int = 5) -> Tuple[str, bool, int, str]:
    """Return (url, ok, status_code, error_message)."""

    req = Request(url, method="HEAD", headers={"User-Agent": "Optimised-WeaponPaints/validator"})
    try:
        with urlopen(req, timeout=timeout) as resp:  # nosec B310
            status = resp.getcode() or 0
            ok = 200 <= status < 400
            return url, ok, status, ""
    except HTTPError as e:
        return url, False, e.code, str(e)
    except URLError as e:
        return url, False, 0, str(e)
    except Exception as e:  # pragma: no cover - unexpected
        return url, False, 0, str(e)


def validate_urls(url_to_files: Dict[str, Set[str]], workers: int = 16) -> List[dict]:
    urls = list(url_to_files.keys())
    total = len(urls)
    print(f"Validating {total} URL(s) with {workers} worker(s)...")

    broken: List[dict] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_url = {executor.submit(check_url, url): url for url in urls}
        for idx, future in enumerate(as_completed(future_to_url), 1):
            url = future_to_url[future]
            try:
                url, ok, status, error = future.result()
            except Exception as exc:  # pragma: no cover
                ok, status, error = False, 0, str(exc)

            if not ok:
                broken.append(
                    {
                        "url": url,
                        "status": status,
                        "error": error,
                        "files": sorted(url_to_files.get(url, [])),
                    }
                )

            if idx % 50 == 0 or idx == total:
                print(f"Checked {idx}/{total} URLs; broken so far: {len(broken)}")

    return broken


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate image URLs referenced in JSON files under the data folder and "
            "write a report of broken links to a JSON file."
        ),
    )
    parser.add_argument(
        "--data-root",
        type=str,
        default="data",
        help="Folder containing JSON data files (default: data)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="broken_image_links.json",
        help="Path (relative to project root) where the report JSON will be written.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=16,
        help="Number of parallel workers for HTTP checks (default: 16)",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    data_root = project_root / args.data_root

    if not data_root.exists():
        print(f"Data folder does not exist: {data_root}")
        return

    url_to_files = collect_image_urls(data_root)

    broken = validate_urls(url_to_files, workers=args.workers)

    report = {
        "total_urls": len(url_to_files),
        "broken_count": len(broken),
        "broken": broken,
    }

    output_path = project_root / args.output
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Written report to {output_path}")
    print(f"Total URLs: {report['total_urls']}, broken: {report['broken_count']}")


if __name__ == "__main__":
    main()
