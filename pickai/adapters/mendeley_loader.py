from __future__ import annotations

from pathlib import Path

import pandas as pd

from pickai.contracts import OrderLine


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str:
    lower_map = {col.lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    raise ValueError(f"Missing expected columns: {candidates}")


def load_mendeley_orderlines(mendeley_dir: str | Path) -> pd.DataFrame:
    base = Path(mendeley_dir)
    waves = pd.read_csv(base / "Picking_Wave.csv")
    storage = pd.read_csv(base / "Storage_Location.csv")

    wave_order = _find_column(waves, ["order_id", "OrderID", "OrderNumber", "order_number"])
    wave_line = _find_column(waves, ["line_id", "LineID", "line_number"])
    wave_sku = _find_column(waves, ["sku", "SKU", "reference", "Reference"])
    wave_loc = _find_column(waves, ["location_id", "LocationID", "location"])
    wave_qty = _find_column(waves, ["quantity", "PCS", "qty"])

    store_loc = _find_column(storage, ["location_id", "LocationID", "location"])
    store_x = _find_column(storage, ["x", "X", "coord_x"])
    store_y = _find_column(storage, ["y", "Y", "coord_y"])
    store_aisle = _find_column(storage, ["aisle", "Aisle", "aisle_id"])
    store_level = _find_column(storage, ["level", "Level", "shelf_level"])

    merged = waves.merge(storage, left_on=wave_loc, right_on=store_loc, how="left")
    out = pd.DataFrame(
        {
            "OrderNumber": merged[wave_order].astype(str),
            "SKU": merged[wave_sku].astype(str),
            "PCS": merged[wave_qty].fillna(1).astype(int),
            "DATE": merged.get("timestamp", merged.get("Timestamp", "2026-01-01")),
            "x": merged[store_x].astype(float),
            "y": merged[store_y].astype(float),
            "aisle": merged[store_aisle].astype(str),
            "level": merged[store_level].astype(str),
            "Coord": merged.apply(lambda r: f"[{r['x']}, {r['y']}]", axis=1),
            "LineID": merged[wave_line].astype(str),
            "LocationID": merged[wave_loc].astype(str),
        }
    )
    return out


def load_mendeley_contracts(mendeley_dir: str | Path) -> list[OrderLine]:
    df = load_mendeley_orderlines(mendeley_dir)
    lines: list[OrderLine] = []
    for idx, row in df.iterrows():
        lines.append(
            OrderLine(
                order_id=str(row["OrderNumber"]),
                line_id=str(row.get("LineID", idx)),
                sku=str(row["SKU"]),
                location_id=str(row.get("LocationID", f"loc-{idx}")),
                quantity=int(row["PCS"]),
                x=float(row["x"]),
                y=float(row["y"]),
            )
        )
    return lines
