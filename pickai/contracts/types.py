from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StorageLocation(BaseModel):
    location_id: str
    x: float
    y: float
    z: float | None = None
    aisle: str | None = None
    level: str | None = None
    zone: str | None = None


class OrderLine(BaseModel):
    order_id: str
    line_id: str
    sku: str
    location_id: str
    quantity: int = Field(ge=1)
    x: float
    y: float
    z: float | None = None
    level: str | None = None
    weight_kg: float | None = None


class EquipmentMode(str, Enum):
    walker = "walker"
    forklift = "forklift"


class LadderState(BaseModel):
    aisle: str | None = None
    level: str | None = None
    x: float
    y: float


class OptimizeConstraints(BaseModel):
    ladder_must_stay_in_aisle: bool = False
    equipment_mode: EquipmentMode = EquipmentMode.walker
    start_position: LadderState | None = None
    depot: LadderState | None = None


class RouteSegment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_location: str = Field(alias="from")
    to_location: str = Field(alias="to")
    segment_type: str
    distance_m: float = Field(ge=0)
    duration_s: float = Field(ge=0)


class OptimizedWave(BaseModel):
    wave_id: str
    sequence: list[RouteSegment]
    total_distance_m: float = Field(ge=0)
    total_duration_s: float = Field(ge=0)
    processing_time_ms: int = Field(ge=0, default=0)
    estimated_picker_time_saved_s: float = Field(default=0)
    ladder_state_after: LadderState | None = None
    picks: list[OrderLine] = Field(default_factory=list)
