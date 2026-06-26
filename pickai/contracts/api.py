from pydantic import BaseModel, Field

from .types import OptimizeConstraints, OptimizedWave, OrderLine


class ResponseMeta(BaseModel):
    request_id: str
    version: str = "v1"


class OptimizeRequest(BaseModel):
    order_lines: list[OrderLine]
    constraints: OptimizeConstraints = Field(default_factory=OptimizeConstraints)
    wave_params: dict[str, int | float | str | bool] | None = None
    idempotency_key: str | None = None


class OptimizeResponseData(BaseModel):
    run_id: str
    status: str
    result: OptimizedWave | None = None


class OptimizeResponse(BaseModel):
    data: OptimizeResponseData
    meta: ResponseMeta


class RunStatus(BaseModel):
    run_id: str
    status: str
    phase: str
    progress: float = Field(ge=0, le=100)
    result: OptimizedWave | None = None
    error: str | None = None
