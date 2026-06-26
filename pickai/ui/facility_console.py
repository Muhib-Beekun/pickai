"""PickAI Facility Console — full map-centric setup and operations."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pickai.contracts import EquipmentMode, LadderState, OptimizeConstraints, OrderLine
from pickai.contracts.facility import (
    AisleDirection,
    AisleRule,
    AisleStatus,
    DockNode,
    FacilityLocation,
    FacilityProfile,
    LocationAttributes,
    PickingMethod,
    PickPolicy,
    TaskLine,
    TaskOptimizeRequest,
    ZoneDef,
)
from pickai.domain.simulation import run_simulation
from pickai.domain.slotting import generate_slotting_suggestions, pick_history_store
from pickai.domain.tasks import optimize_tasks
from pickai.facility.store import facility_store
from pickai.inference.gateway import run_task


def _load_profile() -> FacilityProfile:
    if "facility_profile" not in st.session_state:
        st.session_state.facility_profile = facility_store.load()
    return st.session_state.facility_profile


def _save_profile(profile: FacilityProfile, publish: bool = False) -> FacilityProfile:
    saved = facility_store.publish(profile) if publish else facility_store.save(profile)
    st.session_state.facility_profile = saved
    return saved


def _locations_df(profile: FacilityProfile) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "location_id": loc.location_id,
                "x": loc.x,
                "y": loc.y,
                "aisle": loc.aisle,
                "level": loc.level,
                "zone": loc.zone,
                "blocked": loc.blocked,
                "hazmat": loc.attributes.hazmat,
                "temp_controlled": loc.attributes.temp_controlled,
                "max_weight_kg": loc.attributes.max_weight_kg or 0,
                "pick_height_m": loc.attributes.pick_height_m or 1.2,
            }
            for loc in profile.locations
        ]
    )


def _render_map(
    profile: FacilityProfile,
    heat_df: pd.DataFrame | None = None,
    route_points: list[tuple[float, float]] | None = None,
    highlight_step: int | None = None,
    playback_frames: list[dict] | None = None,
):
    df = _locations_df(profile)
    if df.empty:
        st.warning("No locations in facility profile.")
        return

    color_col = "heat" if heat_df is not None and "heat" in heat_df.columns else None
    plot_df = heat_df if heat_df is not None else df

    fig = px.scatter(
        plot_df,
        x="x",
        y="y",
        color=color_col,
        hover_data=["location_id", "aisle", "zone", "blocked"] if "location_id" in plot_df.columns else None,
        title="Facility map",
        height=520,
    )

    for dock in profile.docks:
        fig.add_trace(
            go.Scatter(
                x=[dock.x],
                y=[dock.y],
                mode="markers+text",
                text=[dock.name],
                textposition="top center",
                marker={"size": 12, "color": "purple", "symbol": "square"},
                name=dock.dock_type,
            )
        )

    for aisle in profile.aisles:
        if aisle.status == AisleStatus.blocked:
            try:
                ax = int(aisle.aisle_id.replace("A", "")) - 1
                fig.add_vrect(x0=ax - 0.4, x1=ax + 0.4, fillcolor="red", opacity=0.15, line_width=0)
            except ValueError:
                pass
        elif aisle.status == AisleStatus.congested:
            try:
                ax = int(aisle.aisle_id.replace("A", "")) - 1
                fig.add_vrect(x0=ax - 0.4, x1=ax + 0.4, fillcolor="orange", opacity=0.12, line_width=0)
            except ValueError:
                pass

    for zone in profile.zones:
        fig.add_shape(
            type="rect",
            x0=zone.x_min,
            x1=zone.x_max,
            y0=zone.y_min,
            y1=zone.y_max,
            line={"color": "cyan", "width": 1, "dash": "dot"},
            fillcolor="cyan" if zone.pedestrian_only else ("yellow" if zone.forklift_only else "rgba(0,0,0,0)"),
            opacity=0.08,
        )

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

    if playback_frames and highlight_step is not None and 0 <= highlight_step < len(playback_frames):
        frame = playback_frames[highlight_step]
        fig.add_trace(
            go.Scatter(
                x=[frame.get("x", 0)],
                y=[frame.get("y", 0)],
                mode="markers",
                marker={"size": 16, "color": "gold", "symbol": "circle"},
                name=f"Step {highlight_step}",
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
        profile.name = st.text_input("Facility name", value=profile.name)
        profile.resources.pickers = st.number_input("Pickers", 1, 32, profile.resources.pickers)
        profile.resources.putters = st.number_input("Putters", 1, 32, profile.resources.putters)
        profile.picking_method = PickingMethod(
            st.selectbox("Picking method", [m.value for m in PickingMethod], index=[m.value for m in PickingMethod].index(profile.picking_method.value))
        )
        profile.pick_policy = PickPolicy(
            st.selectbox("Route policy", [p.value for p in PickPolicy], index=[p.value for p in PickPolicy].index(profile.pick_policy.value))
        )
        profile.task_interleaving = st.selectbox("Task interleaving", ["off", "same_zone", "aggressive"], index=["off", "same_zone", "aggressive"].index(profile.task_interleaving))
        profile.cart_max_lines = st.number_input("Cart max lines", 1, 200, profile.cart_max_lines)
        profile.cart_max_weight_kg = st.number_input("Cart max weight (kg)", 1.0, 2000.0, float(profile.cart_max_weight_kg))
        profile.cart_max_pieces = st.number_input("Cart max pieces", 1, 500, profile.cart_max_pieces)

        st.divider()
        st.caption("Labor standards")
        profile.labor.base_pick_s = st.number_input("Base pick time (s)", 0.5, 30.0, float(profile.labor.base_pick_s))
        profile.labor.golden_zone_min_m = st.number_input("Golden zone min (m)", 0.0, 3.0, float(profile.labor.golden_zone_min_m))
        profile.labor.golden_zone_max_m = st.number_input("Golden zone max (m)", 0.0, 3.0, float(profile.labor.golden_zone_max_m))

        if st.button("Save draft"):
            _save_profile(profile)
            st.success("Draft saved.")
        if st.button("Publish"):
            _save_profile(profile, publish=True)
            st.success(f"Published v{profile.version}.")

    with col1:
        _render_map(profile)

        st.subheader("Location inspector")
        df = _locations_df(profile)
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="loc_editor")
        if st.button("Apply locations"):
            new_locs: list[FacilityLocation] = []
            for _, row in edited.iterrows():
                new_locs.append(
                    FacilityLocation(
                        location_id=str(row["location_id"]),
                        x=float(row["x"]),
                        y=float(row["y"]),
                        aisle=str(row.get("aisle")) if row.get("aisle") else None,
                        level=str(row.get("level")) if row.get("level") else None,
                        zone=str(row.get("zone")) if row.get("zone") else None,
                        blocked=bool(row.get("blocked", False)),
                        attributes=LocationAttributes(
                            hazmat=bool(row.get("hazmat", False)),
                            temp_controlled=bool(row.get("temp_controlled", False)),
                            max_weight_kg=float(row["max_weight_kg"]) if float(row.get("max_weight_kg", 0)) > 0 else None,
                            pick_height_m=float(row.get("pick_height_m", 1.2)),
                        ),
                    )
                )
            profile.locations = new_locs
            _save_profile(profile)
            st.rerun()

        st.subheader("Zones")
        zone_df = st.data_editor(
            pd.DataFrame([z.model_dump() for z in profile.zones]) if profile.zones else pd.DataFrame(),
            num_rows="dynamic",
        )
        if st.button("Apply zones"):
            profile.zones = [ZoneDef(**{k: row[k] for k in ZoneDef.model_fields}) for _, row in zone_df.iterrows()]
            _save_profile(profile)
            st.rerun()

        st.subheader("Docks & staging")
        dock_df = st.data_editor(
            pd.DataFrame([d.model_dump() for d in profile.docks]) if profile.docks else pd.DataFrame(),
            num_rows="dynamic",
        )
        if st.button("Apply docks"):
            profile.docks = [DockNode(**{k: row[k] for k in DockNode.model_fields}) for _, row in dock_df.iterrows()]
            _save_profile(profile)
            st.rerun()

        st.subheader("Aisle rules")
        aisle_df = st.data_editor(
            pd.DataFrame(
                [{"aisle_id": a.aisle_id, "direction": a.direction.value, "status": a.status.value, "blocked": a.blocked} for a in profile.aisles]
            ),
            num_rows="dynamic",
        )
        if st.button("Apply aisles"):
            profile.aisles = [
                AisleRule(
                    aisle_id=str(row["aisle_id"]),
                    direction=AisleDirection(str(row["direction"])),
                    status=AisleStatus(str(row.get("status", "open"))),
                    blocked=bool(row.get("blocked", False)),
                )
                for _, row in aisle_df.iterrows()
                if str(row.get("aisle_id", "")).strip()
            ]
            _save_profile(profile)
            st.rerun()

        uploaded = st.file_uploader("Import pick history CSV", type=["csv"])
        if uploaded and st.button("Load pick history"):
            count = pick_history_store.import_csv(profile.tenant_id, profile.facility_id, uploaded.getvalue().decode("utf-8"))
            st.success(f"Imported {count} pick history rows.")

    st.subheader("Setup chat (NL constraints)")
    chat_text = st.text_area("Describe constraints", placeholder="Forklift, aisle A3 one-way, start x=5 y=10")
    if st.button("Parse with NL"):
        parsed = run_task("nl_parse_optimize", {"text": chat_text})
        st.json(parsed)
        if parsed.get("constraints"):
            st.session_state.parsed_constraints = parsed["constraints"]


def _sample_tasks(n: int, include_put: bool = False, include_replen: bool = False) -> list[TaskLine]:
    profile = _load_profile()
    tasks: list[TaskLine] = []
    for idx, loc in enumerate(profile.locations[:n]):
        tasks.append(
            TaskLine(
                task_type="pick",
                order_id=f"o-{idx // 3}",
                line_id=str(idx),
                sku=f"SKU-{idx % 20}",
                location_id=loc.location_id,
                quantity=1,
                x=loc.x,
                y=loc.y,
                level=loc.level,
                weight_kg=1.5,
            )
        )
    if include_put:
        for loc in profile.locations[:3]:
            tasks.append(TaskLine(task_type="put", order_id="put-1", line_id=f"put-{loc.location_id}", sku="PUT-SKU", location_id=loc.location_id, quantity=1, x=loc.x, y=loc.y, weight_kg=2.0))
    if include_replen:
        for loc in profile.locations[3:6]:
            tasks.append(TaskLine(task_type="replen", order_id="replen-1", line_id=f"replen-{loc.location_id}", sku="REPL-SKU", location_id=loc.location_id, quantity=1, x=loc.x, y=loc.y, weight_kg=3.0))
    return tasks


def render_operations_mode():
    st.subheader("Operations")
    profile = _load_profile()
    constraints_raw = st.session_state.get("parsed_constraints", {})

    col1, col2 = st.columns([2, 1])
    with col2:
        equipment = st.selectbox("Equipment", ["walker", "forklift"])
        ladder_lock = st.checkbox("Ladder stay in aisle", constraints_raw.get("ladder_must_stay_in_aisle", False))
        pick_count = st.slider("Pick lines", 5, 50, 15)
        include_put = st.checkbox("Put tasks", False)
        include_replen = st.checkbox("Replen tasks", False)

        st.caption("Live aisle status")
        aisle_pick = st.selectbox("Aisle", [a.aisle_id for a in profile.aisles] or ["A1"])
        aisle_status = st.selectbox("Status", ["open", "blocked", "congested"])
        if st.button("Update aisle status"):
            for a in profile.aisles:
                if a.aisle_id == aisle_pick:
                    a.status = AisleStatus(aisle_status)
                    a.blocked = aisle_status == "blocked"
            _save_profile(profile)
            st.rerun()

        if st.button("Optimize"):
            tasks = _sample_tasks(pick_count, include_put, include_replen)
            start_raw = constraints_raw.get("start_position", {"x": 0, "y": 5.5, "aisle": "A1", "level": "1"})
            constraints = OptimizeConstraints(
                equipment_mode=EquipmentMode(equipment),
                ladder_must_stay_in_aisle=ladder_lock,
                start_position=LadderState(**start_raw),
            )
            result = optimize_tasks(
                TaskOptimizeRequest(tasks=tasks, constraints=constraints.model_dump(mode="json"), facility_profile_version=profile.version, idempotency_key="console-ops"),
                profile=profile,
            )
            st.session_state.last_result = result.model_dump(mode="json")

        if st.session_state.get("last_result") and st.button("Replan (blocked aisles)"):
            result = optimize_tasks(
                TaskOptimizeRequest(tasks=_sample_tasks(pick_count, include_put, include_replen), idempotency_key="console-replan"),
                profile=profile,
            )
            st.session_state.last_result = result.model_dump(mode="json")

    with col1:
        result = st.session_state.get("last_result")
        if result:
            st.metric("Distance (m)", f"{result['total_distance_m']:.1f}")
            st.metric("Duration (s)", f"{result['total_duration_s']:.1f}")
            st.metric("Labor est. (s)", f"{result.get('labor_estimate_s', 0):.1f}")
            st.metric("Deadhead %", f"{result.get('deadhead_travel_pct', 0):.1f}")
            if result.get("conflict_warnings"):
                st.warning("\n".join(result["conflict_warnings"]))

            frames = result.get("route_playback", [])
            step = st.slider("Route playback step", 0, max(0, len(frames) - 1), 0) if frames else 0

            heat_maps = result.get("heat_maps", [])
            if heat_maps:
                layer = st.selectbox("Heat layer", [h["layer"] for h in heat_maps])
                hm = next(h for h in heat_maps if h["layer"] == layer)
                heat_df = pd.DataFrame(hm["points"]).rename(columns={"value": "heat"})
                _render_map(profile, heat_df=heat_df, playback_frames=frames, highlight_step=step)
            else:
                _render_map(profile, playback_frames=frames, highlight_step=step)

            if result.get("slotting_suggestions"):
                st.subheader("Slotting suggestions")
                st.dataframe(pd.DataFrame(result["slotting_suggestions"]))
        else:
            _render_map(profile)
            st.info("Run optimize to see routes, heat, and playback.")


def render_slotting_mode():
    st.subheader("Slotting — ABC, affinity, move suggestions")
    profile = _load_profile()
    history = pick_history_store.load(profile.tenant_id, profile.facility_id)
    st.caption(f"{len(history)} pick history rows loaded")

    uploaded = st.file_uploader("Upload pick history", type=["csv"], key="slot_upload")
    if uploaded and st.button("Import for slotting"):
        count = pick_history_store.import_csv(profile.tenant_id, profile.facility_id, uploaded.getvalue().decode("utf-8"))
        st.success(f"Imported {count} rows")
        st.rerun()

    suggestions = generate_slotting_suggestions(profile, history, top_n=15)
    if suggestions:
        st.dataframe(pd.DataFrame([s.model_dump() for s in suggestions]))
        saved_m = sum(s.walk_burden_saved_m for s in suggestions)
        st.metric("Total walk burden saved (m)", f"{saved_m:.1f}")
    else:
        st.info("Import pick history CSV (samples/pick_history_sample.csv) to generate slotting suggestions.")

    result = st.session_state.get("last_result")
    if result and result.get("heat_maps"):
        abc = next((h for h in result["heat_maps"] if h["layer"] == "abc_velocity"), None)
        if abc:
            heat_df = pd.DataFrame(abc["points"]).rename(columns={"value": "heat"})
            _render_map(profile, heat_df=heat_df)


def render_simulation_mode():
    st.subheader("What-if simulation")
    profile = _load_profile()
    draft = profile.model_copy(deep=True)
    draft.resources.pickers = st.number_input("Draft pickers", 1, 32, profile.resources.pickers + 1)
    draft.pick_policy = PickPolicy(st.selectbox("Draft route policy", [p.value for p in PickPolicy], index=[p.value for p in PickPolicy].index(profile.pick_policy.value)))
    sample_size = st.slider("Sample size", 20, 200, 80)

    if st.button("Run sample-week simulation"):
        sim = run_simulation(profile, draft, sample_size=sample_size)
        st.session_state.last_sim = sim.model_dump()
        col1, col2, col3 = st.columns(3)
        col1.metric("Baseline distance", f"{sim.baseline_distance_m:.1f} m")
        col2.metric("Draft distance", f"{sim.draft_distance_m:.1f} m")
        col3.metric("ROI", f"{sim.roi_pct:.1f}%")
        st.write(sim.model_dump())


def render_scenario_compare():
    st.subheader("Scenario compare")
    profile = _load_profile()
    draft = profile.model_copy(deep=True)
    draft.resources.pickers = st.number_input("Draft pickers", 1, 32, profile.resources.pickers + 1, key="sc_pickers")
    draft.picking_method = PickingMethod(st.selectbox("Draft method", [m.value for m in PickingMethod], key="sc_method"))

    if st.button("Compare"):
        sim = run_simulation(profile, draft, sample_size=60)
        st.json(sim.model_dump())
