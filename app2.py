# Green Meter App — “screenshot match” version
# One file, dark theme, card layout, pie (Optimized) + bar (Baseline vs Optimized)

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

st.set_page_config(page_title="Green Meter App", page_icon="🌱", layout="wide")
pio.templates.default = "plotly_dark"

# ----------------------------- THEME / CSS -----------------------------
st.markdown("""
<style>
/* App background + text */
[data-testid="stAppViewContainer"] { background-color:#0e1117; color:#ffffff; }

/* Header area */
[data-testid="stHeader"] { background:linear-gradient(90deg, #0e1117 60%, #0c1218 100%) !important; }

/* Buttons (Load sample / Reset / Calculate) */
div.stButton > button {
  background-color:#0bb28b; color:#fff; border:none; border-radius:10px;
  padding:0.45rem 1.0rem; font-weight:700;
}
div.stButton > button:hover { background-color:#10c79c; color:#fff; }

/* “Card” containers */
.card {
  background:#0f141b; border:1px solid #22303a; border-radius:12px;
  padding:14px 16px; margin-bottom:12px;
}

/* Section headers inside cards */
.card h4, .card h5, .card h6 { margin:0 0 6px 0; color:#e6f4ff; }

/* Small gray helper text */
.small { color:#9aa6b2; font-size:0.78rem; margin-top:-6px; margin-bottom:6px; }

/* Assumptions footer card */
.foot-card {
  background:#0f141b; border:1px solid #22303a; border-radius:10px;
  padding:10px 12px; margin-top:6px; color:#bdc7d4; font-size:0.86rem;
}

/* Plotly dark background sync */
.js-plotly-plot .plotly .main-svg { background: #0e1117 !important; }

/* Make Streamlit number inputs roundish to match screenshot */
.stNumberInput input { border-radius:10px !important; }

/* Metric chip spacing */
div[data-testid="stMetric"] { background:#111923; border:1px solid #22303a; border-radius:10px; padding:8px 10px; }
</style>
""", unsafe_allow_html=True)

# ----------------------------- CONSTANTS -----------------------------
KG_PER_TON = 1000.0
EF = {
    "cars": 0.18, "trucks": 0.90, "buses": 1.10, "forklifts": 4.0,
    "planes": 9000.0, "lighting": 0.42, "heating": 0.20,
    "cooling": 0.42, "computing": 0.42
}
CATS = ["cars","trucks","buses","forklifts","planes","lighting","heating","cooling","computing","subcontractors"]
NAMES = {
    "cars":"Cars","trucks":"Trucks","buses":"Buses","forklifts":"Forklifts","planes":"Cargo Planes",
    "lighting":"Office Lighting","heating":"Heating (Thermal)","cooling":"Cooling (A/C)",
    "computing":"Computing (IT)","subcontractors":"Subcontractors"
}
ASSUMPTIONS = (
    "Factors: Cars 0.18 kg/km · Trucks 0.90 kg/km · Buses 1.10 kg/km · "
    "Forklifts 4.0 kg/hr · Planes 9,000 kg/hr · Lighting/Cooling/Computing 0.42 kg/kWh · "
    "Heating 0.20 kg/kWh-th.  EV cars emit ~70% less on the EV share; "
    "KM Reduction scales car distance; Plane Load Factor scales aircraft emissions linearly "
    "(100% = baseline aircraft emissions)."
)

# The sample set that yields Baseline 2802.8 and Optimized 1671.9
SAMPLE = {
    "inputs": dict(
        cars_km=180000, trucks_km=100000, buses_km=60000, forklifts_hr=1500,
        planes_hr=250, lighting_kwh=90000, heating_kwhth=40000,
        cooling_kwh=220000, computing_kwh=60000, subcontractors_tons=[120,45,30]
    ),
    "sliders": dict(ev_share_pct=20, km_reduction_pct=5, plane_load_pct=50)
}

# ----------------------------- CALC FUNCTIONS -----------------------------
def tons_from_kg(kg: float) -> float:
    return kg / KG_PER_TON

def compute_baseline(i: dict) -> dict:
    return {
        "cars":        tons_from_kg(i["cars_km"]      * EF["cars"]),
        "trucks":      tons_from_kg(i["trucks_km"]    * EF["trucks"]),
        "buses":       tons_from_kg(i["buses_km"]     * EF["buses"]),
        "forklifts":   tons_from_kg(i["forklifts_hr"] * EF["forklifts"]),
        "planes":      tons_from_kg(i["planes_hr"]    * EF["planes"]),
        "lighting":    tons_from_kg(i["lighting_kwh"] * EF["lighting"]),
        "heating":     tons_from_kg(i["heating_kwhth"]* EF["heating"]),
        "cooling":     tons_from_kg(i["cooling_kwh"]  * EF["cooling"]),
        "computing":   tons_from_kg(i["computing_kwh"]* EF["computing"]),
        "subcontractors": sum(i["subcontractors_tons"])
    }

def compute_optimized(i: dict, s: dict) -> dict:
    base = compute_baseline(i)
    # Cars: reduce distance, then apply EV intensity discount (EV ≈70% lower)
    km_opt = i["cars_km"] * (1 - s["km_reduction_pct"]/100.0)
    intensity = 1 - 0.70 * (s["ev_share_pct"]/100.0)
    base["cars"] = tons_from_kg(km_opt * EF["cars"] * intensity)
    # Planes: scale by load factor
    base["planes"] = tons_from_kg(i["planes_hr"] * EF["planes"] * (s["plane_load_pct"]/100.0))
    return base

def total(d: dict) -> float:
    return sum(d[c] for c in CATS)

# ----------------------------- STATE & HEADER -----------------------------
st.title("Green Meter App")
st.caption("Carbon-Aware Logistics Dashboard")

# Keep state
if "inputs" not in st.session_state:
    st.session_state.inputs = SAMPLE["inputs"].copy()
if "sliders" not in st.session_state:
    st.session_state.sliders = SAMPLE["sliders"].copy()
i = st.session_state.inputs
s = st.session_state.sliders

# Top control buttons (pill layout)
b1, b2, b3 = st.columns([1,1,1])
with b1:
    if st.button("Load Sample Data"):
        st.session_state.inputs = SAMPLE["inputs"].copy()
        st.session_state.sliders = SAMPLE["sliders"].copy()
        i, s = st.session_state.inputs, st.session_state.sliders
with b2:
    if st.button("Reset"):
        st.session_state.inputs = {k:0 if isinstance(v,(int,float)) else [0,0,0] for k,v in i.items()}
        st.session_state.sliders = {"ev_share_pct":0,"km_reduction_pct":0,"plane_load_pct":100}
        i, s = st.session_state.inputs, st.session_state.sliders
with b3:
    calc_clicked = st.button("Calculate")

st.markdown("---")

# ----------------------------- LAYOUT (Left card / Center pie / Right bar) -----------------------------
left, mid, right = st.columns([1.0, 1.8, 1.4])

# LEFT: Card with inputs + sliders + metrics
with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### INPUTS · ACTIVITY DATA")
    # Inputs with small factor text like the screenshot
    i["cars_km"] = st.number_input("Cars – distance (km / year)", min_value=0.0, value=float(i["cars_km"]), step=1000.0)
    st.markdown('<div class="small">Factor: 0.18 kg CO₂e / km</div>', unsafe_allow_html=True)

    i["trucks_km"] = st.number_input("Trucks – distance (km / year)", min_value=0.0, value=float(i["trucks_km"]), step=1000.0)
    st.markdown('<div class="small">Factor: 0.90 kg CO₂e / km</div>', unsafe_allow_html=True)

    i["buses_km"] = st.number_input("Buses – distance (km / year)", min_value=0.0, value=float(i["buses_km"]), step=1000.0)
    st.markdown('<div class="small">Factor: 1.10 kg CO₂e / km</div>', unsafe_allow_html=True)

    i["forklifts_hr"] = st.number_input("Forklifts – operating time (hours / year)", min_value=0.0, value=float(i["forklifts_hr"]), step=10.0)
    st.markdown('<div class="small">Factor: 4.0 kg CO₂e / hour</div>', unsafe_allow_html=True)

    i["planes_hr"] = st.number_input("Cargo Planes – flight time (hours / year)", min_value=0.0, value=float(i["planes_hr"]), step=10.0)
    st.markdown('<div class="small">Factor: 9,000 kg CO₂e / hour</div>', unsafe_allow_html=True)

    i["lighting_kwh"] = st.number_input("Office Lighting – electricity (kWh / year)", min_value=0.0, value=float(i["lighting_kwh"]), step=1000.0)
    st.markdown('<div class="small">Factor: 0.42 kg CO₂e / kWh</div>', unsafe_allow_html=True)

    i["heating_kwhth"] = st.number_input("Heating – thermal energy (kWh‑th / year)", min_value=0.0, value=float(i["heating_kwhth"]), step=1000.0)
    st.markdown('<div class="small">Factor: 0.20 kg CO₂e / kWh‑th</div>', unsafe_allow_html=True)

    i["cooling_kwh"] = st.number_input("Cooling (A/C) – electricity (kWh / year)", min_value=0.0, value=float(i["cooling_kwh"]), step=1000.0)
    st.markdown('<div class="small">Factor: 0.42 kg CO₂e / kWh</div>', unsafe_allow_html=True)

    i["computing_kwh"] = st.number_input("Computing (IT) – electricity (kWh / year)", min_value=0.0, value=float(i["computing_kwh"]), step=1000.0)
    st.markdown('<div class="small">Factor: 0.42 kg CO₂e / kWh</div>', unsafe_allow_html=True)

    st.markdown("**Subcontractors – tons CO₂e / year (enter 0 if none)**")
    sub1 = st.number_input("Subcontractor #1", min_value=0.0, value=float(i["subcontractors_tons"][0]), step=5.0)
    sub2 = st.number_input("Subcontractor #2", min_value=0.0, value=float(i["subcontractors_tons"][1]), step=5.0)
    sub3 = st.number_input("Subcontractor #3", min_value=0.0, value=float(i["subcontractors_tons"][2]), step=5.0)
    i["subcontractors_tons"] = [sub1, sub2, sub3]
    st.markdown('<div class="small">You can use one, two, or three subcontractors.</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ADJUSTMENTS · SLIDERS")
    s["ev_share_pct"] = st.slider("EV Share for Cars (%)", 0, 100, int(s["ev_share_pct"]))
    st.markdown('<div class="small">Electric cars assumed 70% lower emissions than gasoline.</div>', unsafe_allow_html=True)

    s["km_reduction_pct"] = st.slider("KM Reduction for Cars (%)", 0, 100, int(s["km_reduction_pct"]))
    st.markdown('<div class="small">Trip sharing / better routing reduces car distance.</div>', unsafe_allow_html=True)

    s["plane_load_pct"] = st.slider("Plane Load Factor (%)", 0, 100, int(s["plane_load_pct"]))
    st.markdown('<div class="small">Scaled linearly: 100% = baseline aircraft emissions.</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # end left card

# Compute when “Calculate” pressed
if calc_clicked:
    base = compute_baseline(i)
    opt  = compute_optimized(i, s)
    base_total, opt_total = total(base), total(opt)
    reduction = base_total - opt_total
    pct = (reduction/base_total*100.0) if base_total else 0.0

    # MID: Pie — Optimized shares
    with mid:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### Emission Share by Category (Pie · Optimized)")
        pie_df = pd.DataFrame({
            "Category":[NAMES[c] for c in CATS],
            "Tons":[opt[c] for c in CATS]
        })
        pie_df = pie_df[pie_df["Tons"]>0]
        fig_pie = px.pie(pie_df, names="Category", values="Tons", hole=0.0)
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font_color="#ffffff",
                              legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5))
        st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # RIGHT: Bar — Baseline vs Optimized
    with right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### Total Emissions (tons CO₂e) — Baseline vs Optimized")
        fig_bar = go.Figure()
        fig_bar.add_bar(name="Baseline", x=["Baseline"], y=[base_total])
        fig_bar.add_bar(name="Optimized", x=["Optimized"], y=[opt_total])
        fig_bar.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                              font_color="#ffffff", barmode="group", yaxis_title="tons CO₂e")
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    # LEFT (metrics at bottom like screenshot)
    with left:
        st.metric("Baseline total (tons CO₂e)", f"{base_total:,.1f}")
        st.metric("Optimized total (tons CO₂e)", f"{opt_total:,.1f}")

    # FOOTER ASSUMPTIONS CARD (full width)
    st.markdown('<div class="foot-card">', unsafe_allow_html=True)
    st.markdown(f"**Assumptions** · {ASSUMPTIONS}")
    st.markdown('</div>', unsafe_allow_html=True)
else:
    # Empty placeholders so layout shows like the screenshot before first calc
    with mid:
        st.markdown('<div class="card"><h4>Emission Share by Category (Pie · Optimized)</h4></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="card"><h4>Total Emissions (tons CO₂e) — Baseline vs Optimized</h4></div>', unsafe_allow_html=True)
