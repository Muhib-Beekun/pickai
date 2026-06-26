import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
from utils.routing.distances import (
	distance_picking,
	next_location
)
from utils.routing.routes import (
	create_picking_route
)
from utils.batch.mapping_batch import (
	orderlines_mapping,
	locations_listing
)
from utils.cluster.mapping_cluster import (
	df_mapping
)
from utils.batch.simulation_batch import (
	simulation_wave,
	simulate_batch
)
from utils.cluster.simulation_cluster import(
	loop_wave,
	simulation_cluster,
	create_dataframe,
	process_methods
)
from utils.results.plot import (
	plot_simulation1,
	plot_simulation2
)
import streamlit as st
from streamlit import caching
from pickai.contracts import EquipmentMode, OptimizeConstraints, OptimizeRequest, OrderLine
from pickai.domain.optimizer import optimize_wave
from pickai.adapters.mendeley_loader import load_mendeley_orderlines

# Set page configuration
st.set_page_config(page_title ="Improve Warehouse Productivity using Order Batching",
                    initial_sidebar_state="expanded",
                    layout='wide',
                    page_icon="🛒")

# Set up the page
@st.cache(persist=False,
          allow_output_mutation=True,
          suppress_st_warning=True,
          show_spinner= True)
# Preparation of data
def load(filename, n):
    df_orderlines = pd.read_csv(IN + filename).head(n)
    return df_orderlines


def load_dataset(n, dataset_source, uploaded_file):
	if dataset_source == 'Mendeley':
		mendeley_dir = Path('data/mendeley')
		if mendeley_dir.exists() and (mendeley_dir / 'Picking_Wave.csv').exists() and (mendeley_dir / 'Storage_Location.csv').exists():
			return load_mendeley_orderlines(mendeley_dir).head(n)
	if dataset_source == 'Upload CSV' and uploaded_file is not None:
		df_uploaded = pd.read_csv(uploaded_file)
		if 'Coord' not in df_uploaded.columns and {'x', 'y'}.issubset(set(df_uploaded.columns)):
			df_uploaded['Coord'] = df_uploaded.apply(lambda r: f"[{float(r['x'])}, {float(r['y'])}]", axis=1)
		return df_uploaded.head(n)
	return load('df_lines.csv', n)


def run_domain_optimizer_preview(df_orderlines):
	"""Run a small contract-based optimization preview from current dataframe."""
	sample = df_orderlines.head(25).copy()
	if sample.empty:
		return None

	order_lines = []
	for idx, row in sample.iterrows():
		order_lines.append(
			OrderLine(
				order_id=str(row.get("OrderNumber", idx)),
				line_id=str(idx),
				sku=str(row.get("SKU", "UNKNOWN")),
				location_id=f"loc-{idx}",
				quantity=int(row.get("PCS", 1)),
				x=float(row.get("x")),
				y=float(row.get("y")),
			)
		)

	request = OptimizeRequest(
		order_lines=order_lines,
		constraints=OptimizeConstraints(equipment_mode=EquipmentMode.walker),
		idempotency_key="streamlit-preview",
	)
	return optimize_wave(request)


# Alley Coordinates on y-axis
y_low, y_high = 5.5, 50
# Origin Location
origin_loc = [0, y_low]
# Distance Threshold (m)			
distance_threshold = 35			
distance_list = [1] + [i for i in range(5, 100, 5)]		
IN = 'static/in/'
# Dataset source controls
mendeley_available = Path('data/mendeley/Picking_Wave.csv').exists() and Path('data/mendeley/Storage_Location.csv').exists()
dataset_default = 'Mendeley' if mendeley_available else 'Original'
dataset_source = st.sidebar.selectbox('Dataset source', ['Original', 'Mendeley', 'Upload CSV'], index=['Original', 'Mendeley', 'Upload CSV'].index(dataset_default))
uploaded_csv = st.sidebar.file_uploader('Upload order lines CSV', type=['csv']) if dataset_source == 'Upload CSV' else None

# Store Results by WaveID
list_wid, list_dst, list_route, list_ord, list_lines, list_pcs, list_monomult = [], [], [], [], [], [], []
list_results = [list_wid, list_dst, list_route, list_ord, list_lines, list_pcs, list_monomult]	# Group in list
# Store Results by Simulation (Order_number)
list_ordnum , list_dstw = [], []

# Simulation 1: Order Batch
# SCOPE SIZE
st.header("**🥇 Impact of the wave size in orders (Orders/Wave) **")
st.subheader('''
        🛠️ HOW MANY ORDER LINES DO YOU WANT TO INCLUDE IN YOUR ANALYSIS?
    ''')
col1, col2 = st.beta_columns(2)
with col1:
	n = st.slider(
				'SIMULATION 1 SCOPE (THOUSDAND ORDERS)', 1, 200 , value = 5)
with col2:
	lines_number = 1000 * n 
	st.write('''🛠️{:,} \
		order lines'''.format(lines_number))
# SIMULATION PARAMETERS
st.subheader('''
        🛠️ SIMULATE ORDER PICKING BY WAVE OF N ORDERS PER WAVE WITH N IN [N_MIN, N_MAX] ''')
col_11 , col_22 = st.beta_columns(2)
with col_11:
	n1 = st.slider(
				'SIMULATION 1: N_MIN (ORDERS/WAVE)', 0, 20 , value = 1)
	n2 = st.slider(
				'SIMULATION 1: N_MAX (ORDERS/WAVE)', n1 + 1, 20 , value = int(np.max([n1+1 , 10])))
with col_22:
		st.write('''[N_MIN, N_MAX] = [{:,}, {:,}]'''.format(n1, n2))
# START CALCULATION
start_1= False
if st.checkbox('SIMULATION 1: START CALCULATION',key='show', value=False):
    start_1 = True
# Calculation
if start_1:
	df_orderlines = load_dataset(lines_number, dataset_source, uploaded_csv)
	df_waves, df_results = simulate_batch(n1, n2, y_low, y_high, origin_loc, lines_number, df_orderlines)
	plot_simulation1(df_results, lines_number)
	preview = run_domain_optimizer_preview(df_orderlines)
	if preview is not None:
		st.caption("Domain optimizer preview distance: {:,.0f} m".format(preview.total_distance_m))

# Simulation 2: Order Batch using Spatial Clustering 
# SCOPE SIZE
st.header("**🥈 Impact of the order batching method **")
st.subheader('''
        🛠️ HOW MANY ORDER LINES DO YOU WANT TO INCLUDE IN YOUR ANALYSIS?
    ''')
col1, col2 = st.beta_columns(2)
with col1:
	n_ = st.slider(
				'SIMULATION 2 SCOPE (THOUSDAND ORDERS)', 1, 200 , value = 5)
with col2:
	lines_2 = 1000 * n_ 
	st.write('''🛠️{:,} \
		order lines'''.format(lines_2))
# START CALCULATION
start_2 = False
if st.checkbox('SIMULATION 2: START CALCULATION',key='show_2', value=False):
    start_2 = True
# Calculation
if start_2:
	df_orderlines = load_dataset(lines_2, dataset_source, uploaded_csv)
	df_reswave, df_results = simulation_cluster(y_low, y_high, df_orderlines, list_results, n1, n2, 
			distance_threshold)
	plot_simulation2(df_reswave, lines_2, distance_threshold)