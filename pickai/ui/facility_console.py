"""PickAI Facility Console — map-centric setup and operations."""

from __future__ import annotations

import json

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pickai.contracts import EquipmentMode, LadderState, OptimizeConstraints, OrderLine
from pickai.contracts.facility import AisleDirection, AisleRule, FacilityProfile, PickingMethod, TaskLine, TaskOptimizeRequest
from pickai.domain.optimizer import optimize_wave
from pickai.domain.tasks import optimize_tasks
from pickai.facility.store import facility_store
from pickai.inference.gateway import run_task

API_BASE = st.session_state.get("api_base", "http://localhost:8000")
API_KEY = st.session_state.get("api_key", "dev")


def _api_headers() -> dict:
    return {"X-API-Key": API_KEY}


def _load_profile() -> FacilityProfile:
    if "facility_profile" not in st.session_state:
        st.session_state.facility_profile = facility_store.load()
    return st.session_state.facility_profile


def _save_profile(profile: FacilityProfile, publish: bool = False) -> FacilityProfile:
    saved = facility_store.publish(profile) if publish else facility_store.save(profile)
    st.session_state.facility_profile = saved
    return saved


def _locations_df(profile: FacilityProfile) -> pd.DataFrame:
    rows = [
        {
            "location_id": loc.location_id,
            "x": loc.x,
            "y": loc.y,
            "aisle": loc.aisle,
            "level": loc.level,
            "zone": loc.zone,
            "blocked": loc.blocked,
        }
        for loc in profile.locations
    ]
    return pd.DataFrame(rows)


def _render_map(profile: FacilityProfile, heat_layer: str | None = None, route_points: list[tuple[float, float]] | None = None):
    df = _locations_df(profile)
    if df.empty:
        st.warning("No locations in facility profile. Import location_master.csv or add locations.")
        return

    color_col = None
    if heat_layer == "pick_density" and "heat" in df.columns:
        color_col = "heat"
    elif heat_layer == "walk_burden":
        staging_x = profile.layout.staging_x or profile.layout.origin_x
        staging_y = profile.layout.staging_y or profile.layout.origin_y
        df["heat"] = ((df["x"] - staging_x) ** 2 + (df["y"] - staging_y) ** 2) ** 0.5
        color_col = "heat"

    fig = px.scatter(
        df,
        x="x",
        y="y",
        color=color_col,
        hover_data=["location_id", "aisle", "zone", "blocked"],
        title="Facility map",
        height=520,
    )

    for aisle in profile.aisles:
        if aisle.direction == AisleDirection.increasing:
            symbol = "▲"
        elif aisle.direction == AisleDirection.decreasing:
            symbol = "▼"
        else:
            continue
        try:
            aisle_num = int(aisle.aisle_id.replace("A", "")) - 1
            fig.add_annotation(x=aisle_num, y=profile.layout.y_low, text=symbol, showarrow=False)
        except ValueError:
            pass

    if route_points:
        fig.add_trace(
            go.Scatter(
                x=[p[0] for p in route_points],
                y=[p[1] for p in route_points],
                mode="lines+markers",
                line={"color": "lime", "width": 3},
                name="Route",
            )
        )

    staging_x = profile.layout.staging_x or profile.layout.origin_x
    staging_y = profile.layout.staging_y or profile.layout.origin_y
    fig.add_trace(
        go.Scatter(
            x=[staging_x],
            y=[staging_y],
            mode="markers",
            marker={"size": 14, "color": "red", "symbol": "star"},
            name="Staging",
        )
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    st.plotly_chart(fig, use_container_width=True)


def render_setup_mode():
    st.subheader("Setup — facility profile")
    profile = _load_profile()

    col1, col2 = st.columns([2, 1])
    with col2:
        st.metric("Profile version", profile.version)
        st.metric("Locations", len(profile.locations))
        st.metric("Pickers / Putters", f"{profile.resources.pickers} / {profile.resources.putters}")

        profile.name = st.text_input("Facility name", value=profile.name)
        profile.resources.pickers = st.number_input("Pickers", min_value=1, max_value=32, value=profile.resources.pickers)
        profile.resources.putters = st.number_input("Putters", min_value=1, max_value=32, value=profile.resources.putters)
        method = st.selectbox(
            "Picking method",
            ["discrete", "batch", "wave", "zone"],
            index=["discrete", "batch", "wave", "zone"].index(profile.picking_method.value),
        )
        profile.picking_method = PickingMethod(method)
        profile.task_interleaving = st.selectbox("Task interleaving", ["off", "same_zone", "aggressive"], index=["off", "same_zone", "aggressive"].index(profile.task_interleaving))

        st.divider()
        st.caption("Inference (BYOK)")
        profile.inference.provider = st.selectbox(
            "Provider",
            ["ollama", "openai", "anthropic", "azure", "custom"],
            index=["ollama", "openai", "anthropic", "azure", "custom"].index(profile.inference.provider.value),
        )
        profile.inference.model = st.text_input("Model", value=profile.inference.model)
        profile.inference.api_key_env = st.text_input("API key env var", value=profile.inference.api_key_env or "")
        profile.inference.base_url = st.text_input("Base URL", value=profile.inference.base_url or "")

        if st.button("Save draft"):
            _save_profile(profile)
            st.success("Draft saved.")
        if st.button("Publish new version"):
            _save_profile(profile, publish=True)
            st.success(f"Published v{profile.version}.")

    with col1:
        heat_layer = st.selectbox("Heat overlay", ["none", "walk_burden"], index=0)
        _render_map(profile, heat_layer=None if heat_layer == "none" else heat_layer)

        st.caption("Click a location row to edit blocked state and aisle rules.")
        df = _locations_df(profile)
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="loc_editor")
        if st.button("Apply location edits"):
            new_locs = []
            for _, row in edited.iterrows():
                existing = next((l for l in profile.locations if l.location_id == row["location_id"]), None)
                if existing:
                    existing.blocked = bool(row.get("blocked", False))
                    existing.x = float(row["x"])
                    existing.y = float(row["y"])
                    new_locs.append(existing)
            profile.locations = new_locs
            _save_profile(profile)
            st.rerun()

        st.subheader("Aisle rules")
        aisle_rows = [{"aisle_id": a.aisle_id, "direction": a.direction.value, "blocked": a.blocked} for a in profile.aisles]
        aisle_df = st.data_editor(pd.DataFrame(aisle_rows) if aisle_rows else pd.DataFrame(columns=["aisle_id", "direction", "blocked"]), num_rows="dynamic")
        if st.button("Apply aisle rules"):
            profile.aisles = [
                AisleRule(
                    aisle_id=str(row["aisle_id"]),
                    direction=AisleDirection(str(row["direction"])),
                    blocked=bool(row.get("blocked", False)),
                )
                for _, row in aisle_df.iterrows()
                if str(row.get("aisle_id", "")).strip()
            ]
            _save_profile(profile)
            st.rerun()

    st.subheader("Setup chat")
    chat_text = st.text_area("Describe facility constraints", placeholder="Forklift in aisle A3 one-way increasing, start at x=5 y=10")
    if st.button("Parse with NL"):
        parsed = run_task("nl_parse_optimize", {"text": chat_text})
        st.json(parsed)
        constraints = parsed.get("constraints", {})
        if constraints:
            st.session_state.parsed_constraints = constraints


def _sample_order_lines(n: int = 15) -> list[OrderLine]:
    profile = _load_profile()
    lines: list[OrderLine] = []
    for idx, loc in enumerate(profile.locations[:n]):
        lines.append(
            OrderLine(
                order_id=f"o-{idx // 3}",
                line_id=str(idx),
                sku=f"SKU-{idx}",
                location_id=loc.location_id,
                quantity=1,
                x=loc.x,
                y=loc.y,
                level=loc.level,
            )
        )
    return lines


def render_operations_mode():
    st.subheader("Operations — optimize and heat maps")
    profile = _load_profile()
    constraints_raw = st.session_state.get("parsed_constraints", {})
    equipment = constraints_raw.get("equipment_mode", "walker")
    ladder_lock = constraints_raw.get("ladder_must_stay_in_aisle", False)
    start_raw = constraints_raw.get("start_position", {"x": 0, "y": 5.5, "aisle": "A1", "level": "1"})

    col1, col2 = st.columns([2, 1])
    with col2:
        equipment = st.selectbox("Equipment", ["walker", "forklift"], index=0 if equipment == "walker" else 1)
        ladder_lock = st.checkbox("Ladder must stay in aisle", value=ladder_lock)
        pick_count = st.slider("Sample pick lines", 5, 40, 15)
        include_put = st.checkbox("Include put tasks", value=False)
        if st.button("Run multi-resource optimize"):
            pick_lines = _sample_order_lines(pick_count)
            tasks = [TaskLine(task_type="pick", **line.model_dump()) for line in pick_lines]
            if include_put:
                for line in pick_lines[:3]:
                    tasks.append(TaskLine(task_type="put", **line.model_dump()))
            constraints = OptimizeConstraints(
                equipment_mode=EquipmentMode(equipment),
                ladder_must_stay_in_aisle=ladder_lock,
                start_position=LadderState(**start_raw),
            )
            request = TaskOptimizeRequest(
                tasks=tasks,
                constraints=constraints.model_dump(mode="json"),
                facility_profile_version=profile.version,
                idempotency_key="console-ops",
            )
            result = optimize_tasks(request, profile=profile)
            st.session_state.last_result = result.model_dump(mode="json")

    with col1:
        result = st.session_state.get("last_result")
        if result:
            st.metric("Total distance (m)", f"{result['total_distance_m']:.1f}")
            st.metric("Total duration (s)", f"{result['total_duration_s']:.1f}")
            st.metric("Empty travel %", f"{result['empty_travel_pct']:.1f}")
            if result.get("conflict_warnings"):
                st.warning("\n".join(result["conflict_warnings"]))

            route_points: list[tuple[float, float]] = []
            for assignment in result.get("assignments", []):
                seq = assignment.get("result", {}).get("sequence", [])
                for seg in seq:
                    if seg.get("segment_type") == "walk":
                        label = seg.get("to", "")
                        if label.startswith("("):
                            parts = label.strip("()").split(",")
                            route_points.append((float(parts[0]), float(parts[1])))

            heat_maps = result.get("heat_maps", [])
            layer_names = [hm["layer"] for hm in heat_maps]
            selected = st.selectbox("Heat layer", layer_names) if layer_names else None
            if selected:
                hm = next(h for h in heat_maps if h["layer"] == selected)
                df = pd.DataFrame(hm["points"])
                fig = px.scatter(df, x="x", y="y", color="value", title=f"Heat: {selected}", height=400)
                st.plotly_chart(fig, use_container_width=True)
            _render_map(profile, route_points=route_points or None)
            with st.expander("Full result JSON"):
                st.json(result)
        else:
            _render_map(profile)
            st.info("Run optimize to see routes and heat maps.")


def render_scenario_compare():
    st.subheader("Scenario compare (draft vs published)")
    profile = _load_profile()
    draft = profile.model_copy(deep=True)
    draft.resources.pickers = st.number_input("Draft pickers", min_value=1, max_value=32, value=profile.resources.pickers + 1, key="draft_pickers")

    if st.button("Compare scenarios"):
        lines = _sample_order_lines(20)
        base_constraints = OptimizeConstraints()
        base_req = TaskOptimizeRequest(
            tasks=[TaskLine(task_type="pick", **l.model_dump()) for l in lines],
            constraints=base_constraints.model_dump(mode="json"),
            idempotency_key="compare-base",
        )
        draft_req = TaskOptimizeRequest(
            tasks=[TaskLine(task_type="pick", **l.model_dump()) for l in lines],
            constraints=base_constraints.model_dump(mode="json"),
            resources=draft.resources,
            idempotency_key="compare-draft",
        )
        base_result = optimize_tasks(base_req, profile=profile)
        draft_result = optimize_tasks(draft_req, profile=draft)
        saved_m = base_result.total_distance_m - draft_result.total_distance_m
        st.write(
            {
                "published_distance_m": base_result.total_distance_m,
                "draft_distance_m": draft_result.total_distance_m,
                "distance_delta_m": saved_m,
                "published_conflicts": len(base_result.conflict_warnings),
                "draft_conflicts": len(draft_result.conflict_warnings),
            }
        )
