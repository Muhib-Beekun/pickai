from __future__ import annotations

import itertools

import pandas as pd

from .routing import parse_coord


def orderlines_mapping(df_orderlines: pd.DataFrame, orders_number: int) -> tuple[pd.DataFrame, int]:
    """Map order lines to waves based on order chronology and target orders per wave."""
    df = df_orderlines.copy()
    date_col = "DATE" if "DATE" in df.columns else None
    if date_col:
        df.sort_values(by=date_col, ascending=True, inplace=True)

    list_orders = df.OrderNumber.unique()
    dict_map = dict(zip(list_orders, [i for i in range(1, len(list_orders) + 1)]))
    df["OrderID"] = df["OrderNumber"].map(dict_map)
    df["WaveID"] = (df.OrderID % orders_number == 0).shift(1).fillna(0).cumsum()
    waves_number = int(df.WaveID.max()) + 1
    return df, waves_number


def locations_listing(df_orderlines: pd.DataFrame, wave_id: int) -> tuple[list[list[float]], int]:
    """Return unique sorted coordinate list for a given wave id."""
    df = df_orderlines[df_orderlines.WaveID == wave_id]
    list_locs = [parse_coord(item) for item in df["Coord"].values]
    list_locs.sort()
    list_locs = list(k for k, _ in itertools.groupby(list_locs))
    return list_locs, len(list_locs)
