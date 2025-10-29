# Green Meter App — Streamlit + Plotly
# Paste this entire file into GitHub as app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Green Meter App", page_icon="🌱", layout="wide")

# ---------- constants ----------
KG_PER_TON = 1000.0
EF = {  # kg CO2e per unit
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
    "Factors — Cars 0.18 kg/km; Trucks 0.90; Buses 1.10; Forklifts 4.0 kg/hr; "
    "Cargo Planes 9,000 kg/hr; Electricity (Lighting/Cooling/Computing) 0.42 kg/kWh; "
    "Heating 0.20 kg/kWh-th.  EV share reduces EV portion by ~70%. "
    "KM Reduction lowers car distance. Plane Load Factor scales aircraft linearly (100% = baseline)."
)

SAMPLE = {
    "inputs": dict(
        cars_km=180000, trucks_km=100000, buses_km=60000, forklifts_hr=1500,
        planes_hr=250, lighting_kwh=90000, heating_kwhth=40000,
        cooling_kwh=220000, computing_kwh=60000, subcontractors_tons=[120,45,30]
    ),
    "sliders": dict(ev_share_pct=20, km_reduction_pct=5, plane_load_pct=50)
}

# ---------- helpers ----------
def tons_from_kg(kg: float) -> float: return kg / KG_PER_TON

def compute_baseline(i):
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
        "subcontractors": sum(i["subcontractors_tons"]),
    }

def compute_optimized(i, s):
    base = compute_baseline(i)
    # Cars: km cut then EV intensity (EVs ~70% less)
    km_opt = i["cars_km"] * (1 - s["km_reduction_pct"]/100.0)
    intensity = 1 - 0.70 * (s["ev_share_pct"]/100.0)
    base["cars"] = tons_from_kg(km_opt * EF["cars"] * intensity)
    # Planes: scale by load factor
    base["planes"] = tons_from_kg(i["planes_hr"] * EF["planes"] * (s["plane_load_pct"]/100.0))
    return base

def total(d): return sum(d[c] for c in CATS)

# ---------- UI ----------
st.title("Green Meter App")
st.caption("Carbon-Aware Logistics Dashboard")

# top buttons
c1, c2, c3 = st.columns([1,1,1])
if "inputs" not in st.session_state: st.session_state.inputs = SAMPLE["inputs"].copy()
if "sliders" not in st.session_state: st.session_state.sliders = SAMPLE["sliders"].copy()
i = st.session_state.inputs
s = st.session_state.sliders

with c1:
    if st.button("Load Sample Data"):
        st.session_state.inputs = SAMPLE["inputs"].copy()
        st.session_state.sliders = SAMPLE["sliders"].copy()
with c2:
    if st.button("Reset"):
        st.session_state.inputs = {k:0 if isinstance(v,(int,float)) else [0,0,0] for k,v in i.items()}
        st.session_state.sliders = {"ev_share_pct":0,"km_reduction_pct":0,"plane_load_pct":100}
with c3:
    calc = st.button("Calculate", type="primary")

st.markdown("---")

# left inputs
left, mid, right = st.columns([1.1,1.5,1.2])
with left:
    st.subheader("Inputs – Activity Data")
    i["cars_km"] = st.number_input("Cars – distance (km/year)", 0.0, value=float(i["cars_km"]))
    i["trucks_km"] = st.number_input("Trucks – distance (km/year)", 0.0, value=float(i["trucks_km"]))
    i["buses_km"] = st.number_input("Buses – distance (km/year)", 0.0, value=float(i["buses_km"]))
    i["forklifts_hr"] = st.number_input("Forklifts – operating time (hours/year)", 0.0, value=float(i["forklifts_hr"]))
    i["planes_hr"] = st.number_input("Cargo Planes – flight time (hours/year)", 0.0, value=float(i["planes_hr"]))
    i["lighting_kwh"] = st.number_input("Office Lighting – electricity (kWh/year)", 0.0, value=float(i["lighting_kwh"]))
    i["heating_kwhth"] = st.number_input("Heating – thermal energy (kWh-th/year)", 0.0, value=float(i["heating_kwhth"]))
    i["cooling_kwh"] = st.number_input("Cooling (A/C) – electricity (kWh/year)", 0.0, value=float(i["cooling_kwh"]))
    i["computing_kwh"] = st.number_input("Computing (IT) – electricity (kWh/year)", 0.0, value=float(i["computing_kwh"]))
    st.markdown("**Subcontractors — tons CO₂e/year**")
    sub1 = st.number_input("Subcontractor #1", 0.0, value=float(i["subcontractors_tons"][0]))
    sub2 = st.number_input("Subcontractor #2", 0.0, value=float(i["subcontractors_tons"][1]))
    sub3 = st.number_input("Subcontractor #3", 0.0, value=float(i["subcontractors_tons"][2]))
    i["subcontractors_tons"] = [sub1, sub2, sub3]
    st.markdown("### Adjustments – Sliders")
    s["ev_share_pct"] = st.slider("EV Share for Cars (%)", 0, 100, int(s["ev_share_pct"]))
    s["km_reduction_pct"] = st.slider("KM Reduction for Cars (%)", 0, 100, int(s["km_reduction_pct"]))
    s["plane_load_pct"] = st.slider("Plane Load Factor (%)", 0, 100, int(s["plane_load_pct"]))

# calculations
if calc:
    base = compute_baseline(i)
    opt = compute_optimized(i, s)
    base_total, opt_total = total(base), total(opt)
    reduction = base_total - opt_total
    pct = 0 if base_total==0 else reduction/base_total*100

    df = pd.DataFrame({
        "Category":[NAMES[c] for c in CATS],
        "Baseline":[base[c] for c in CATS],
        "Optimized":[opt[c] for c in CATS]
    })
    df["Reduction"] = df["Baseline"] - df["Optimized"]

    with left:
        st.metric("Baseline total (tons CO₂e)", f"{base_total:,.1f}")
        st.metric("Optimized total (tons CO₂e)", f"{opt_total:,.1f}")
        st.metric("Reduction (tons)", f"{reduction:,.1f}")
        st.metric("Percent reduction", f"{pct:.1f}%")

    with mid:
        st.subheader("Emission Share by Category (Pie – Optimized)")
        pie_df = df[df["Optimized"]>0]
        fig_pie = px.pie(pie_df, names="Category", values="Optimized")
        st.plotly_chart(fig_pie, use_container_width=True)

    with right:
        st.subheader("Total Emissions — Baseline vs Optimized")
        fig_bar = go.Figure()
        fig_bar.add_bar(name="Baseline", x=["Baseline"], y=[base_total])
        fig_bar.add_bar(name="Optimized", x=["Optimized"], y=[opt_total])
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("### Assumptions")
    st.info(ASSUMPTIONS)
