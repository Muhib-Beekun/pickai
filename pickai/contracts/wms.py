from pydantic import BaseModel, Field

from .types import OrderLine


class WmsOrderExport(BaseModel):
    warehouse_id: str | None = None
    lines: list[OrderLine]
    field_mapping: dict[str, str] = Field(default_factory=dict)


class WmsWebhookPayload(BaseModel):
    event: str = "wave_released"
    warehouse_id: str
    lines: list[OrderLine]
