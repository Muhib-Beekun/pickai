from __future__ import annotations

import json
from pathlib import Path

from pickai.contracts.facility import FacilityProfile

from .defaults import build_default_profile


class FacilityStore:
    def __init__(self, root: str | Path = "data/facilities") -> None:
        self.root = Path(root)

    def _path(self, tenant_id: str, facility_id: str) -> Path:
        return self.root / tenant_id / f"{facility_id}.json"

    def load(self, tenant_id: str = "default", facility_id: str = "main") -> FacilityProfile:
        path = self._path(tenant_id, facility_id)
        if not path.exists():
            profile = build_default_profile(tenant_id=tenant_id, facility_id=facility_id)
            self.save(profile)
            return profile
        data = json.loads(path.read_text(encoding="utf-8"))
        return FacilityProfile.model_validate(data)

    def save(self, profile: FacilityProfile) -> FacilityProfile:
        path = self._path(profile.tenant_id, profile.facility_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        return profile

    def publish(self, profile: FacilityProfile) -> FacilityProfile:
        profile.version += 1
        return self.save(profile)

    def export_geojson(self, profile: FacilityProfile) -> dict:
        features: list[dict] = []
        for loc in profile.locations:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [loc.x, loc.y]},
                    "properties": {
                        "location_id": loc.location_id,
                        "aisle": loc.aisle,
                        "level": loc.level,
                        "zone": loc.zone,
                        "blocked": loc.blocked,
                        **loc.attributes.model_dump(),
                    },
                }
            )
        for aisle in profile.aisles:
            features.append(
                {
                    "type": "Feature",
                    "geometry": None,
                    "properties": {
                        "type": "aisle_rule",
                        "aisle_id": aisle.aisle_id,
                        "direction": aisle.direction.value,
                        "blocked": aisle.blocked,
                    },
                }
            )
        return {"type": "FeatureCollection", "features": features}


facility_store = FacilityStore()
