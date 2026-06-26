"""Domain-level wrappers around existing clustering simulation utilities."""

from __future__ import annotations

import pandas as pd

from utils.cluster.mapping_cluster import df_mapping as _df_mapping
from utils.cluster.simulation_cluster import simulation_cluster as _simulation_cluster


def map_with_clustering(
    df_orderlines: pd.DataFrame,
    orders_number: int,
    distance_threshold: float,
    mono_method: str,
    multi_method: str,
) -> tuple[pd.DataFrame, int]:
    return _df_mapping(df_orderlines, orders_number, distance_threshold, mono_method, multi_method)


def run_cluster_simulation(
    y_low: float,
    y_high: float,
    df_orderlines: pd.DataFrame,
    list_results: list[list],
    n1: int,
    n2: int,
    distance_threshold: float,
):
    return _simulation_cluster(y_low, y_high, df_orderlines, list_results, n1, n2, distance_threshold)
