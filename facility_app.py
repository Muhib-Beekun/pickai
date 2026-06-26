import streamlit as st

from pickai.ui.facility_console import (
    render_operations_mode,
    render_scenario_compare,
    render_setup_mode,
    render_simulation_mode,
    render_slotting_mode,
)

st.set_page_config(page_title="PickAI Facility Console", layout="wide", page_icon="🏭")
st.title("PickAI Facility Console")
st.caption("Map-centric setup, operations, slotting, and simulation.")

mode = st.sidebar.radio(
    "Mode",
    ["Setup", "Operations", "Slotting", "Simulation", "Scenario compare"],
    index=0,
)
st.sidebar.markdown("---")
st.sidebar.markdown("[API docs](http://localhost:8000/docs)")
st.sidebar.markdown("[Legacy simulation](http://localhost:8501)")

if mode == "Setup":
    render_setup_mode()
elif mode == "Operations":
    render_operations_mode()
elif mode == "Slotting":
    render_slotting_mode()
elif mode == "Simulation":
    render_simulation_mode()
else:
    render_scenario_compare()
