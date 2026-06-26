from __future__ import annotations

from pickai.contracts import OptimizedWave
from pickai.contracts.facility import RoutePlaybackFrame


def build_route_playback(result: OptimizedWave | dict) -> list[RoutePlaybackFrame]:
    if isinstance(result, dict):
        sequence = result.get("sequence", [])
    else:
        sequence = [s.model_dump(by_alias=True) for s in result.sequence]

    frames: list[RoutePlaybackFrame] = []
    step = 0
    for seg in sequence:
        seg_type = seg.get("segment_type", "walk")
        frm = seg.get("from", "")
        to = seg.get("to", "")
        x, y = 0.0, 0.0
        label = to if seg_type == "pick" else to
        if isinstance(label, str) and label.startswith("("):
            parts = label.strip("()").split(",")
            x, y = float(parts[0]), float(parts[1])
        frames.append(
            RoutePlaybackFrame(
                step=step,
                segment_type=seg_type,
                from_label=str(frm),
                to_label=str(to),
                x=x,
                y=y,
                distance_m=float(seg.get("distance_m", 0)),
                duration_s=float(seg.get("duration_s", 0)),
            )
        )
        step += 1
    return frames
