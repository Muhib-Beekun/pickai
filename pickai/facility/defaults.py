from __future__ import annotations

import csv
import json
from pathlib import Path

from pickai.contracts.facility import (
    AisleDirection,
    AisleRule,
    FacilityLayout,
    FacilityLocation,
    FacilityProfile,
    ZoneDef,
)


def _load_aisle_rules() -> dict[str, str]:
    path = Path("data/fixtures/aisle_rules.json")
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("one_way", {})


def build_default_profile(tenant_id: str = "default", facility_id: str = "main") -> FacilityProfile:
    layout = FacilityLayout(y_low=5.5, y_high=50.0, origin_x=0.0, origin_y=5.5, staging_x=0.0, staging_y=5.5)
    locations: list[FacilityLocation] = []

    loc_csv = Path("samples/location_master.csv")
    if loc_csv.exists():
        with loc_csv.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                locations.append(
                    FacilityLocation(
                        location_id=row["location_id"],
                        x=float(row["x"]),
                        y=float(row["y"]),
                        aisle=row.get("aisle"),
                        level=row.get("level"),
                        zone=f"Z{int(float(row['x']) // 8) + 1}",
                    )
                )

    one_way = _load_aisle_rules()
    aisles = [
        AisleRule(
            aisle_id=aisle_id,
            direction=AisleDirection(direction) if direction in ("increasing", "decreasing") else AisleDirection.two_way,
        )
        for aisle_id, direction in one_way.items()
    ]

    zones = [
        ZoneDef(zone_id="Z1", name="West", x_min=0, x_max=11, y_min=5.5, y_max=50),
        ZoneDef(zone_id="Z2", name="Center", x_min=12, x_max=23, y_min=5.5, y_max=50),
        ZoneDef(zone_id="Z3", name="East", x_min=24, x_max=35, y_min=5.5, y_max=50),
    ]

    return FacilityProfile(
        tenant_id=tenant_id,
        facility_id=facility_id,
        version=1,
        name="Main facility",
        layout=layout,
        locations=locations,
        aisles=aisles,
        zones=zones,
    )
