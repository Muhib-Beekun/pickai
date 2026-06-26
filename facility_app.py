import streamlit as st

from pickai.ui.facility_console import render_operations_mode, render_scenario_compare, render_setup_mode

st.set_page_config(page_title="PickAI Facility Console", layout="wide", page_icon="🏭")
st.title("PickAI Facility Console")
st.caption("Map-centric setup and operations. WMS-adjacent — not a WMS.")

mode = st.sidebar.radio("Mode", ["Setup", "Operations", "Scenario compare"], index=0)
st.sidebar.markdown("---")
st.sidebar.markdown("[API docs](http://localhost:8000/docs)")
st.sidebar.markdown("[Legacy simulation](http://localhost:8501)")

if mode == "Setup":
    render_setup_mode()
elif mode == "Operations":
    render_operations_mode()
else:
    render_scenario_compare()
