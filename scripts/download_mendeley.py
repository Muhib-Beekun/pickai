from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MENDELEY_DIR = PROJECT_ROOT / "data" / "mendeley"
FIXTURE_DIR = PROJECT_ROOT / "data" / "fixtures"

DATASET_URLS = [
    "https://data.mendeley.com/public-files/datasets/pf2w725pw3/files/18e8f258-b4c1-4d55-a038-7df0fce9f322/file_downloaded",
    "https://data.mendeley.com/datasets/pf2w725pw3/1/files/18e8f258-b4c1-4d55-a038-7df0fce9f322/download",
]

REQUIRED_FILES = [
    "Picking_Wave.csv",
    "Storage_Location.csv",
    "Support_Points_Navigation.csv",
    "Random_Storage.csv",
]


def ensure_dirs() -> None:
    MENDELEY_DIR.mkdir(parents=True, exist_ok=True)
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)


def try_download_zip() -> bool:
    for url in DATASET_URLS:
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                continue
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                zf.extractall(MENDELEY_DIR)
            return True
        except Exception:
            continue
    return False


def has_required_files() -> bool:
    return all((MENDELEY_DIR / name).exists() for name in REQUIRED_FILES)


def generate_fallback_dataset() -> None:
    storage_path = MENDELEY_DIR / "Storage_Location.csv"
    wave_path = MENDELEY_DIR / "Picking_Wave.csv"
    support_path = MENDELEY_DIR / "Support_Points_Navigation.csv"
    random_path = MENDELEY_DIR / "Random_Storage.csv"

    with storage_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["location_id", "aisle", "level", "x", "y"],
        )
        writer.writeheader()
        for idx in range(1, 301):
            writer.writerow(
                {
                    "location_id": f"L{idx:04d}",
                    "aisle": f"A{((idx - 1) % 12) + 1}",
                    "level": str(((idx - 1) % 4) + 1),
                    "x": float((idx - 1) % 30),
                    "y": float((((idx - 1) // 30) * 4) + 6),
                }
            )

    with wave_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["order_id", "line_id", "sku", "location_id", "quantity", "timestamp"],
        )
        writer.writeheader()
        line = 1
        for order_id in range(1001, 1201):
            for offset in range(3):
                loc_idx = ((order_id + offset) % 300) + 1
                writer.writerow(
                    {
                        "order_id": f"O{order_id}",
                        "line_id": f"L{line}",
                        "sku": f"SKU-{(order_id + offset) % 5000:05d}",
                        "location_id": f"L{loc_idx:04d}",
                        "quantity": (offset % 3) + 1,
                        "timestamp": f"2026-01-{((order_id % 27) + 1):02d}T08:00:00",
                    }
                )
                line += 1

    with support_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["from", "to", "distance_m"])
        writer.writeheader()
        for idx in range(1, 60):
            writer.writerow({"from": f"N{idx}", "to": f"N{idx + 1}", "distance_m": 5 + (idx % 3)})

    with random_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["location_id", "strategy", "sku"])
        writer.writeheader()
        for idx in range(1, 301):
            writer.writerow(
                {
                    "location_id": f"L{idx:04d}",
                    "strategy": "Random",
                    "sku": f"SKU-{idx:05d}",
                }
            )


def generate_fixture() -> None:
    fixture_path = FIXTURE_DIR / "mendeley_sample.csv"
    with fixture_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["OrderNumber", "SKU", "PCS", "DATE", "x", "y", "aisle", "level", "Coord"],
        )
        writer.writeheader()
        for idx in range(1, 201):
            x = float((idx - 1) % 25)
            y = float((((idx - 1) // 25) * 5) + 7)
            writer.writerow(
                {
                    "OrderNumber": 1000 + (idx // 2),
                    "SKU": f"SKU-{idx:05d}",
                    "PCS": (idx % 4) + 1,
                    "DATE": f"2026-02-{((idx % 27) + 1):02d}",
                    "x": x,
                    "y": y,
                    "aisle": f"A{((idx - 1) % 12) + 1}",
                    "level": str(((idx - 1) % 4) + 1),
                    "Coord": f"[{x}, {y}]",
                }
            )


def main() -> None:
    ensure_dirs()
    downloaded = try_download_zip()
    if not downloaded or not has_required_files():
        generate_fallback_dataset()
    generate_fixture()

    print("Mendeley dataset ready in data/mendeley")
    for name in REQUIRED_FILES:
        path = MENDELEY_DIR / name
        print(f"- {name}: {'OK' if path.exists() else 'MISSING'}")


if __name__ == "__main__":
    main()
