import pandas as pd
import pytest
import os

from pickai.contracts import EquipmentMode, OptimizeConstraints, OptimizeRequest, OrderLine
from pickai.domain.batching import locations_listing, orderlines_mapping
from pickai.domain.optimizer import optimize_wave
from pickai.domain.routing import create_picking_route


def test_orderlines_mapping_and_locations_listing():
    df = pd.DataFrame(
        [
            {"OrderNumber": 1, "DATE": "2024-01-01", "Coord": "[1, 10]"},
            {"OrderNumber": 2, "DATE": "2024-01-02", "Coord": "[2, 12]"},
            {"OrderNumber": 2, "DATE": "2024-01-02", "Coord": "[2, 12]"},
        ]
    )
    mapped, waves_number = orderlines_mapping(df, orders_number=1)
    assert waves_number >= 1
    locs, n_locs = locations_listing(mapped, wave_id=0)
    assert n_locs >= 1
    assert isinstance(locs[0], list)


def test_create_picking_route_returns_distance_and_path():
    distance, path = create_picking_route([0, 5.5], [[1, 10], [2, 20]], 5.5, 50)
    assert distance > 0
    assert path[0] == [0, 5.5]
    assert path[-1] == [0, 5.5]


def test_optimize_wave_produces_segments():
    request = OptimizeRequest(
        order_lines=[
            OrderLine(order_id="o1", line_id="l1", sku="a", location_id="loc-a", quantity=1, x=1, y=9),
            OrderLine(order_id="o1", line_id="l2", sku="b", location_id="loc-b", quantity=1, x=3, y=15),
        ],
        constraints=OptimizeConstraints(equipment_mode=EquipmentMode.walker),
        idempotency_key="wave-test",
    )
    result = optimize_wave(request)
    assert result.wave_id == "wave-test"
    assert result.total_distance_m > 0
    assert len(result.sequence) >= 1


def test_ladder_relocate_segment_inserted_on_cross_aisle():
    request = OptimizeRequest(
        order_lines=[
            OrderLine(order_id="o1", line_id="l1", sku="a", location_id="loc-a", quantity=1, x=1, y=9),
            OrderLine(order_id="o1", line_id="l2", sku="b", location_id="loc-b", quantity=1, x=8, y=15),
        ],
        constraints=OptimizeConstraints(equipment_mode=EquipmentMode.walker, ladder_must_stay_in_aisle=False),
        idempotency_key="wave-relocate",
    )
    result = optimize_wave(request)
    assert any(segment.segment_type == "ladder_relocate" for segment in result.sequence)


def test_ladder_stay_in_aisle_constraint_blocks_cross_aisle_route():
    request = OptimizeRequest(
        order_lines=[
            OrderLine(order_id="o1", line_id="l1", sku="a", location_id="loc-a", quantity=1, x=1, y=9),
            OrderLine(order_id="o1", line_id="l2", sku="b", location_id="loc-b", quantity=1, x=8, y=15),
        ],
        constraints=OptimizeConstraints(equipment_mode=EquipmentMode.walker, ladder_must_stay_in_aisle=True),
        idempotency_key="wave-stay",
    )
    with pytest.raises(ValueError):
        optimize_wave(request)


def test_ortools_route_is_not_worse_than_heuristic():
    order_lines = [
        OrderLine(order_id="o1", line_id="l1", sku="a", location_id="loc-a", quantity=1, x=1, y=9),
        OrderLine(order_id="o1", line_id="l2", sku="b", location_id="loc-b", quantity=1, x=7, y=18),
        OrderLine(order_id="o1", line_id="l3", sku="c", location_id="loc-c", quantity=1, x=3, y=12),
        OrderLine(order_id="o1", line_id="l4", sku="d", location_id="loc-d", quantity=1, x=10, y=22),
    ]

    request = OptimizeRequest(
        order_lines=order_lines,
        constraints=OptimizeConstraints(equipment_mode=EquipmentMode.walker, ladder_must_stay_in_aisle=False),
        idempotency_key="solver-compare",
    )

    os.environ["PICKAI_SOLVER"] = "heuristic"
    heuristic = optimize_wave(request)
    os.environ["PICKAI_SOLVER"] = "ortools"
    ortools = optimize_wave(request)

    assert ortools.total_distance_m <= heuristic.total_distance_m


def test_ladder_state_and_time_saved_fields_present():
    os.environ["PICKAI_SOLVER"] = "ortools"
    request = OptimizeRequest(
        order_lines=[
            OrderLine(order_id="o1", line_id="l1", sku="a", location_id="loc-a", quantity=1, x=1, y=9, level="1"),
            OrderLine(order_id="o1", line_id="l2", sku="b", location_id="loc-b", quantity=1, x=4, y=16, level="3"),
            OrderLine(order_id="o1", line_id="l3", sku="c", location_id="loc-c", quantity=1, x=8, y=12, level="2"),
        ],
        constraints=OptimizeConstraints(equipment_mode=EquipmentMode.walker, ladder_must_stay_in_aisle=False),
        idempotency_key="ladder-fields",
    )
    result = optimize_wave(request)
    assert result.ladder_state_after is not None
    assert result.processing_time_ms >= 0
    assert result.estimated_picker_time_saved_s >= 0
