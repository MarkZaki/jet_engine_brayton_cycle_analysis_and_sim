from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import plotly.graph_objects as go
import streamlit as st

from configs.default import get_default_config
from models.atmosphere import isa_atmosphere
from performance.metrics import summarize_result
from solver.engine import run_engine_case, sweep_compressor_pressure_ratio
from visualization.plots import plot_PV, plot_TP, plot_TS, plot_engine_flow, plot_performance


def _build_sidebar_config():
    defaults = get_default_config()
    st.sidebar.header("Inputs")

    altitude_m = st.sidebar.slider("Altitude (m)", 0, 15000, int(defaults["altitude_m"]), step=250)
    atmosphere = isa_atmosphere(float(altitude_m))

    config = dict(defaults)
    config["altitude_m"] = float(altitude_m)
    config["ambient_temperature"] = atmosphere.temperature
    config["ambient_pressure"] = atmosphere.pressure
    config["flight_speed"] = st.sidebar.slider("Flight Speed (m/s)", 0.0, 450.0, float(defaults["flight_speed"]), step=5.0)
    config["mass_flow_rate"] = st.sidebar.slider("Mass Flow Rate (kg/s)", 1.0, 80.0, float(defaults["mass_flow_rate"]), step=1.0)

    st.sidebar.caption(
        f"ISA ambient: {atmosphere.temperature:.1f} K, {atmosphere.pressure / 1000.0:.1f} kPa"
    )

    with st.sidebar.expander("Component Settings", expanded=True):
        config["pressure_recovery"] = st.slider(
            "Diffuser Pressure Recovery",
            0.85,
            1.0,
            float(defaults["pressure_recovery"]),
            step=0.01,
            key="pressure_recovery",
        )
        config["compressor_pressure_ratio"] = st.slider(
            "Compressor Pressure Ratio",
            2.0,
            30.0,
            float(defaults["compressor_pressure_ratio"]),
            step=0.5,
            key="compressor_pressure_ratio",
        )
        config["compressor_efficiency"] = st.slider(
            "Compressor Efficiency",
            0.70,
            0.95,
            float(defaults["compressor_efficiency"]),
            step=0.01,
            key="compressor_efficiency",
        )
        config["turbine_inlet_temperature"] = st.slider(
            "Turbine Inlet Temperature (K)",
            900.0,
            2200.0,
            float(defaults["turbine_inlet_temperature"]),
            step=25.0,
            key="turbine_inlet_temperature",
        )
        config["combustor_pressure_loss"] = st.slider(
            "Combustor Pressure Loss",
            0.0,
            0.12,
            float(defaults["combustor_pressure_loss"]),
            step=0.005,
            key="combustor_pressure_loss",
        )
        config["combustor_efficiency"] = st.slider(
            "Combustor Efficiency",
            0.90,
            1.0,
            float(defaults["combustor_efficiency"]),
            step=0.005,
            key="combustor_efficiency",
        )
        config["turbine_efficiency"] = st.slider(
            "Turbine Efficiency",
            0.75,
            0.98,
            float(defaults["turbine_efficiency"]),
            step=0.01,
            key="turbine_efficiency",
        )
        config["mechanical_efficiency"] = st.slider(
            "Mechanical Efficiency",
            0.85,
            1.0,
            float(defaults["mechanical_efficiency"]),
            step=0.01,
            key="mechanical_efficiency",
        )
        config["nozzle_efficiency"] = st.slider(
            "Nozzle Efficiency",
            0.80,
            1.0,
            float(defaults["nozzle_efficiency"]),
            step=0.01,
            key="nozzle_efficiency",
        )

    with st.sidebar.expander("Gas Model", expanded=False):
        config["gas_cp"] = st.number_input("cp (J/kg-K)", value=float(defaults["gas_cp"]), step=5.0)
        config["gas_gamma"] = st.number_input("gamma", value=float(defaults["gas_gamma"]), step=0.01)
        config["fuel_lower_heating_value"] = st.number_input(
            "Fuel LHV (J/kg)",
            value=float(defaults["fuel_lower_heating_value"]),
            step=500000.0,
            format="%.0f",
        )

    config["verbose"] = False
    return config


def _metric_card(label, value, help_text=None):
    st.metric(label, value, help=help_text)


def _sweep_figure(sweep_df):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sweep_df["compressor_pressure_ratio"],
            y=sweep_df["thrust_N"],
            mode="lines+markers",
            name="Thrust (N)",
            line={"color": "#0F6CBD", "width": 3},
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sweep_df["compressor_pressure_ratio"],
            y=sweep_df["overall_efficiency"],
            mode="lines+markers",
            name="Overall efficiency",
            line={"color": "#C44536", "width": 3, "dash": "dash"},
            yaxis="y2",
        )
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#F6F8FB",
        plot_bgcolor="#FFFFFF",
        title={"text": "Compressor Pressure-Ratio Sweep", "x": 0.04},
        margin={"l": 60, "r": 60, "t": 70, "b": 50},
        xaxis={"title": "Compressor Pressure Ratio"},
        yaxis={"title": "Thrust (N)", "gridcolor": "#D9E2EC"},
        yaxis2={
            "title": "Overall Efficiency",
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        },
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1.0},
    )
    return fig


def main():
    st.set_page_config(page_title="Jet Engine Brayton Simulator", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.4rem; padding-bottom: 1.2rem;}
        .hero {
            padding: 1.2rem 1.4rem;
            border-radius: 16px;
            background: linear-gradient(120deg, #102A43 0%, #0F6CBD 55%, #A3C4DC 100%);
            color: #F6F8FB;
            margin-bottom: 1rem;
        }
        .hero p {margin: 0.35rem 0 0 0; color: rgba(246,248,251,0.88);}
        </style>
        <div class="hero">
            <h2 style="margin:0;">Jet Engine Brayton Cycle Analysis</h2>
            <p>Interactive 1D cycle model with actual vs theoretical plots, station records, and a thermal-flow schematic.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    config = _build_sidebar_config()
    result = run_engine_case(config)
    summary = summarize_result(result, V0=config["flight_speed"])
    station_df = result.to_dataframe()

    metrics = st.columns(6)
    with metrics[0]:
        _metric_card("Thrust", f"{summary['thrust_N']:.1f} N")
    with metrics[1]:
        _metric_card("Specific Thrust", f"{summary['specific_thrust_N_per_kg_s']:.1f}")
    with metrics[2]:
        _metric_card("Fuel-Air Ratio", f"{summary['fuel_air_ratio']:.5f}")
    with metrics[3]:
        _metric_card("BWR", f"{summary['bwr']:.3f}")
    with metrics[4]:
        _metric_card("Overall Eff.", f"{summary['overall_efficiency']:.3f}")
    with metrics[5]:
        _metric_card("Nozzle Choked", "Yes" if summary["nozzle_choked"] else "No")

    tabs = st.tabs(["Cycle Plots", "Engine View", "Parametric Sweep", "Stations"])

    with tabs[0]:
        left, right = st.columns(2)
        left.plotly_chart(plot_TS(result, show=False, persist=False), width="stretch")
        right.plotly_chart(plot_PV(result, show=False, persist=False), width="stretch")
        left, right = st.columns(2)
        left.plotly_chart(plot_TP(result, show=False, persist=False), width="stretch")
        right.plotly_chart(plot_performance(result, show=False, persist=False), width="stretch")

    with tabs[1]:
        branch = st.radio("Schematic branch", ["Actual", "Theoretical"], horizontal=True)
        st.plotly_chart(
            plot_engine_flow(result, ideal=(branch == "Theoretical"), show=False, persist=False),
            width="stretch",
        )

    with tabs[2]:
        sweep_cols = st.columns(3)
        pr_min = sweep_cols[0].slider("Min pressure ratio", 2.0, 20.0, 4.0, step=0.5)
        pr_max = sweep_cols[1].slider("Max pressure ratio", 5.0, 30.0, 20.0, step=0.5)
        n_points = sweep_cols[2].slider("Sweep points", 4, 20, 9, step=1)
        if pr_min >= pr_max:
            st.warning("Min pressure ratio must be smaller than max pressure ratio.")
        else:
            pressure_ratios = [pr_min + i * (pr_max - pr_min) / (n_points - 1) for i in range(n_points)]
            sweep_df = sweep_compressor_pressure_ratio(config, pressure_ratios)
            st.plotly_chart(_sweep_figure(sweep_df), width="stretch")
            st.dataframe(sweep_df.round(4), width="stretch", hide_index=True)

    with tabs[3]:
        st.dataframe(station_df.round(4), width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
