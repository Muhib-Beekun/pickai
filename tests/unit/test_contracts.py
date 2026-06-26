from pickai.contracts import (
    EquipmentMode,
    OptimizeConstraints,
    OptimizeRequest,
    OrderLine,
    RouteSegment,
)


def test_optimize_request_contract_accepts_valid_payload():
    payload = OptimizeRequest(
        order_lines=[
            OrderLine(
                order_id="o1",
                line_id="l1",
                sku="sku-1",
                location_id="loc-1",
                quantity=1,
                x=1,
                y=10,
            )
        ],
        constraints=OptimizeConstraints(equipment_mode=EquipmentMode.walker),
    )
    assert payload.order_lines[0].order_id == "o1"


def test_route_segment_aliases_from_to_fields():
    segment = RouteSegment(**{"from": "A", "to": "B"}, segment_type="walk", distance_m=10, duration_s=7)
    dumped = segment.model_dump(by_alias=True)
    assert dumped["from"] == "A"
    assert dumped["to"] == "B"
