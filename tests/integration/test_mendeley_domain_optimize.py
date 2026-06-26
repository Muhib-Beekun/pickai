import pandas as pd

from pickai.contracts import EquipmentMode, OptimizeConstraints, OptimizeRequest, OrderLine
from pickai.domain.optimizer import optimize_wave


def test_optimize_mendeley_fixture_produces_valid_wave():
    df = pd.read_csv("data/fixtures/mendeley_sample.csv").head(40)
    order_lines = []
    for idx, row in df.iterrows():
        order_lines.append(
            OrderLine(
                order_id=str(row["OrderNumber"]),
                line_id=str(idx),
                sku=str(row["SKU"]),
                location_id=f"fixture-{idx}",
                quantity=int(row["PCS"]),
                x=float(row["x"]),
                y=float(row["y"]),
            )
        )

    request = OptimizeRequest(
        order_lines=order_lines,
        constraints=OptimizeConstraints(equipment_mode=EquipmentMode.walker),
        idempotency_key="fixture-wave",
    )
    result = optimize_wave(request)

    assert result.total_distance_m > 0
    assert result.sequence
    assert result.wave_id == "fixture-wave"
