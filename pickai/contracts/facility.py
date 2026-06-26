from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AisleDirection(str, Enum):
    two_way = "two_way"
    increasing = "increasing"
    decreasing = "decreasing"


class AisleStatus(str, Enum):
    open = "open"
    blocked = "blocked"
    congested = "congested"


class AisleRule(BaseModel):
    aisle_id: str
    direction: AisleDirection = AisleDirection.two_way
    blocked: bool = False
    status: AisleStatus = AisleStatus.open


class DockNode(BaseModel):
    dock_id: str
    name: str
    x: float
    y: float
    dock_type: str = "staging"


class LaborConfig(BaseModel):
    base_pick_s: float = 3.0
    golden_zone_min_m: float = 0.8
    golden_zone_max_m: float = 1.6
    height_penalty_per_m: float = 2.0


class VelocityTier(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class PickHistoryRecord(BaseModel):
    order_id: str
    sku: str
    location_id: str
    quantity: int = Field(ge=1)
    x: float
    y: float


class SlottingSuggestion(BaseModel):
    sku: str
    from_location_id: str
    to_location_id: str
    walk_burden_saved_m: float
    reason: str


class RoutePlaybackFrame(BaseModel):
    step: int
    segment_type: str
    from_label: str
    to_label: str
    x: float
    y: float
    distance_m: float = 0.0
    duration_s: float = 0.0


class SimulationResult(BaseModel):
    sample_size: int
    baseline_distance_m: float
    draft_distance_m: float
    distance_saved_m: float
    baseline_duration_s: float
    draft_duration_s: float
    duration_saved_s: float
    roi_pct: float
    baseline_conflicts: int = 0
    draft_conflicts: int = 0


class ZoneDef(BaseModel):
    zone_id: str
    name: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    pedestrian_only: bool = False
    forklift_only: bool = False
    attributes: dict[str, str | bool | float] = Field(default_factory=dict)


class LocationAttributes(BaseModel):
    temp_controlled: bool = False
    hazmat: bool = False
    max_weight_kg: float | None = None
    pick_height_m: float | None = None


class FacilityLocation(BaseModel):
    location_id: str
    x: float
    y: float
    z: float | None = None
    aisle: str | None = None
    level: str | None = None
    zone: str | None = None
    attributes: LocationAttributes = Field(default_factory=LocationAttributes)
    blocked: bool = False


class ResourcePool(BaseModel):
    pickers: int = Field(default=1, ge=1, le=32)
    putters: int = Field(default=1, ge=1, le=32)


class PickPolicy(str, Enum):
    shortest_path = "shortest_path"
    s_shape = "s_shape"
    largest_gap = "largest_gap"
    combined = "combined"
    return_policy = "return_policy"


class PutPolicy(str, Enum):
    nearest_empty = "nearest_empty"


class PickingMethod(str, Enum):
    discrete = "discrete"
    batch = "batch"
    wave = "wave"
    zone = "zone"


class HeatLayer(str, Enum):
    pick_density = "pick_density"
    walk_burden = "walk_burden"
    congestion = "congestion"
    abc_velocity = "abc_velocity"
    sku_affinity = "sku_affinity"


class HeatConfig(BaseModel):
    layers: list[HeatLayer] = Field(
        default_factory=lambda: [HeatLayer.pick_density, HeatLayer.walk_burden, HeatLayer.congestion]
    )


class InferenceProvider(str, Enum):
    ollama = "ollama"
    openai = "openai"
    anthropic = "anthropic"
    azure = "azure"
    custom = "custom"


class InferenceProfile(BaseModel):
    provider: InferenceProvider = InferenceProvider.ollama
    model: str = "qwen2.5:7b-instruct"
    api_key_env: str | None = None
    base_url: str | None = None


class FacilityLayout(BaseModel):
    y_low: float = 5.5
    y_high: float = 50.0
    origin_x: float = 0.0
    origin_y: float = 5.5
    staging_x: float | None = None
    staging_y: float | None = None


class FacilityProfile(BaseModel):
    tenant_id: str = "default"
    facility_id: str = "main"
    version: int = 1
    name: str = "Main facility"
    layout: FacilityLayout = Field(default_factory=FacilityLayout)
    locations: list[FacilityLocation] = Field(default_factory=list)
    aisles: list[AisleRule] = Field(default_factory=list)
    zones: list[ZoneDef] = Field(default_factory=list)
    docks: list[DockNode] = Field(default_factory=list)
    resources: ResourcePool = Field(default_factory=ResourcePool)
    pick_policy: PickPolicy = PickPolicy.shortest_path
    put_policy: PutPolicy = PutPolicy.nearest_empty
    picking_method: PickingMethod = PickingMethod.wave
    heat_config: HeatConfig = Field(default_factory=HeatConfig)
    inference: InferenceProfile = Field(default_factory=InferenceProfile)
    labor: LaborConfig = Field(default_factory=LaborConfig)
    cart_max_lines: int = Field(default=50, ge=1)
    cart_max_weight_kg: float = Field(default=200.0, ge=1)
    cart_max_pieces: int = Field(default=200, ge=1)
    task_interleaving: str = "off"


class HeatPoint(BaseModel):
    location_id: str
    x: float
    y: float
    value: float = Field(ge=0)


class HeatMap(BaseModel):
    layer: HeatLayer
    points: list[HeatPoint] = Field(default_factory=list)
    max_value: float = 0.0


class ResourceAssignment(BaseModel):
    resource_id: str
    resource_type: str
    zone_id: str | None = None
    order_lines: list[str] = Field(default_factory=list)
    result: dict | None = None
    conflict_warnings: list[str] = Field(default_factory=list)


class TaskLine(BaseModel):
    task_type: str = "pick"
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


class TaskOptimizeRequest(BaseModel):
    tasks: list[TaskLine]
    constraints: dict | None = None
    facility_profile_version: int | None = None
    resources: ResourcePool | None = None
    idempotency_key: str | None = None


class TaskOptimizeResult(BaseModel):
    run_id: str
    assignments: list[ResourceAssignment]
    heat_maps: list[HeatMap] = Field(default_factory=list)
    slotting_suggestions: list[SlottingSuggestion] = Field(default_factory=list)
    route_playback: list[RoutePlaybackFrame] = Field(default_factory=list)
    total_distance_m: float = 0.0
    total_duration_s: float = 0.0
    labor_estimate_s: float = 0.0
    processing_time_ms: int = 0
    empty_travel_pct: float = 0.0
    deadhead_travel_pct: float = 0.0
    conflict_warnings: list[str] = Field(default_factory=list)
