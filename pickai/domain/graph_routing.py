from __future__ import annotations

from pickai.contracts.facility import FacilityProfile, FacilityLocation
from pickai.domain.routing import distance_picking


class FacilityGraph:
    """Walkable graph from facility locations for distance queries."""

    def __init__(self, profile: FacilityProfile) -> None:
        self.profile = profile
        self.nodes: dict[str, tuple[float, float]] = {}
        for loc in profile.locations:
            self.nodes[loc.location_id] = (loc.x, loc.y)
        for dock in profile.docks:
            self.nodes[dock.dock_id] = (dock.x, dock.y)
        staging = profile.layout.staging_x or profile.layout.origin_x
        staging_y = profile.layout.staging_y or profile.layout.origin_y
        self.nodes["__staging__"] = (staging, staging_y)

    def distance(self, a_id: str, b_id: str) -> float:
        a = self.nodes[a_id]
        b = self.nodes[b_id]
        y_low = self.profile.layout.y_low
        y_high = self.profile.layout.y_high
        return float(distance_picking(list(a), list(b), y_low, y_high))

    def nearest(self, from_id: str, candidates: list[FacilityLocation]) -> FacilityLocation | None:
        if not candidates:
            return None
        return min(candidates, key=lambda loc: self.distance(from_id, loc.location_id))
