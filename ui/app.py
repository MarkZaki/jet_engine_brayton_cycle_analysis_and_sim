import json
from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from configs.default import get_default_config
from models.atmosphere import isa_atmosphere
from performance.metrics import summarize_result
from performance.reporting import build_html_report
import solver.engine as engine_module
from visualization.plots import (
    figure_to_html_bytes,
    figure_to_png_bytes,
    plot_PV,
    plot_TP,
    plot_TS,
    plot_engine_flow,
    plot_operating_map,
    plot_performance,
)

run_engine_case = engine_module.run_engine_case
sweep_compressor_pressure_ratio = engine_module.sweep_compressor_pressure_ratio


def _fallback_sweep_flight_envelope(base_config, altitudes_m, flight_speeds_mps):
    rows = []

    for altitude_m in altitudes_m:
        atmosphere = isa_atmosphere(float(altitude_m))
        for flight_speed in flight_speeds_mps:
            case_config = dict(base_config)
            case_config["altitude_m"] = float(altitude_m)
            case_config["ambient_temperature"] = atmosphere.temperature
            case_config["ambient_pressure"] = atmosphere.pressure
            case_config["flight_speed"] = float(flight_speed)
            case_config["verbose"] = False
            result = run_engine_case(case_config)
            summary = summarize_result(result, V0=case_config["flight_speed"])
            rows.append(
                {
                    "altitude_m": float(altitude_m),
                    "flight_speed_mps": float(flight_speed),
                    "thrust_N": summary["thrust_N"],
                    "specific_thrust_N_per_kg_s": summary["specific_thrust_N_per_kg_s"],
                    "overall_efficiency": summary["overall_efficiency"],
                    "jet_power_efficiency": summary["jet_power_efficiency"],
                    "nozzle_choked": summary["nozzle_choked"],
                }
            )

    return pd.DataFrame(rows)


sweep_flight_envelope = getattr(engine_module, "sweep_flight_envelope", _fallback_sweep_flight_envelope)


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
        )
        config["compressor_pressure_ratio"] = st.slider(
            "Compressor Pressure Ratio",
            2.0,
            30.0,
            float(defaults["compressor_pressure_ratio"]),
            step=0.5,
        )
        config["compressor_efficiency"] = st.slider(
            "Compressor Efficiency",
            0.70,
            0.95,
            float(defaults["compressor_efficiency"]),
            step=0.01,
        )
        config["turbine_inlet_temperature"] = st.slider(
            "Turbine Inlet Temperature (K)",
            900.0,
            2200.0,
            float(defaults["turbine_inlet_temperature"]),
            step=25.0,
        )
        config["combustor_pressure_loss"] = st.slider(
            "Combustor Pressure Loss",
            0.0,
            0.12,
            float(defaults["combustor_pressure_loss"]),
            step=0.005,
        )
        config["combustor_efficiency"] = st.slider(
            "Combustor Efficiency",
            0.90,
            1.0,
            float(defaults["combustor_efficiency"]),
            step=0.005,
        )
        config["turbine_efficiency"] = st.slider(
            "Turbine Efficiency",
            0.75,
            0.98,
            float(defaults["turbine_efficiency"]),
            step=0.01,
        )
        config["mechanical_efficiency"] = st.slider(
            "Mechanical Efficiency",
            0.85,
            1.0,
            float(defaults["mechanical_efficiency"]),
            step=0.01,
        )
        config["nozzle_efficiency"] = st.slider(
            "Nozzle Efficiency",
            0.80,
            1.0,
            float(defaults["nozzle_efficiency"]),
            step=0.01,
        )

    with st.sidebar.expander("Section Velocities", expanded=False):
        config["diffuser_exit_velocity"] = st.slider(
            "Diffuser Exit Velocity (m/s)",
            20.0,
            220.0,
            float(defaults["diffuser_exit_velocity"]),
            step=5.0,
        )
        config["compressor_exit_velocity"] = st.slider(
            "Compressor Exit Velocity (m/s)",
            40.0,
            260.0,
            float(defaults["compressor_exit_velocity"]),
            step=5.0,
        )
        config["combustor_exit_velocity"] = st.slider(
            "Combustor Exit Velocity (m/s)",
            20.0,
            180.0,
            float(defaults["combustor_exit_velocity"]),
            step=5.0,
        )
        config["turbine_exit_velocity"] = st.slider(
            "Turbine Exit Velocity (m/s)",
            40.0,
            280.0,
            float(defaults["turbine_exit_velocity"]),
            step=5.0,
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


def _station_column_view(station_df, mode):
    if mode == "Actual Focus":
        return station_df[
            [
                "stage_name",
                "stage_index",
                "actual_static_temperature_K",
                "actual_total_temperature_K",
                "actual_static_pressure_kPa",
                "actual_total_pressure_kPa",
                "actual_velocity_mps",
                "actual_mach",
                "actual_area_m2",
                "actual_entropy_J_per_kgK",
                "fuel_air_ratio",
                "nozzle_choked",
            ]
        ]
    if mode == "Theoretical Focus":
        return station_df[
            [
                "stage_name",
                "stage_index",
                "ideal_static_temperature_K",
                "ideal_total_temperature_K",
                "ideal_static_pressure_kPa",
                "ideal_total_pressure_kPa",
                "ideal_velocity_mps",
                "ideal_mach",
                "ideal_area_m2",
                "ideal_entropy_J_per_kgK",
                "fuel_air_ratio",
                "nozzle_choked",
            ]
        ]
    return station_df


def _download_buttons(figures, station_df, component_df, summary):
    report_html = build_html_report(
        summary,
        {
            "station_csv": Path("station_summary.csv"),
            "component_csv": Path("component_summary.csv"),
            "summary_json": Path("summary_metrics.json"),
        },
    ).encode("utf-8")

    left, right = st.columns(2)
    with left:
        st.download_button(
            "Download Station CSV",
            station_df.to_csv(index=False).encode("utf-8"),
            file_name="station_summary.csv",
            mime="text/csv",
            width="stretch",
        )
        st.download_button(
            "Download Component CSV",
            component_df.to_csv(index=False).encode("utf-8"),
            file_name="component_summary.csv",
            mime="text/csv",
            width="stretch",
        )
        st.download_button(
            "Download Summary JSON",
            json.dumps(summary, indent=2).encode("utf-8"),
            file_name="summary_metrics.json",
            mime="application/json",
            width="stretch",
        )
    with right:
        st.download_button(
            "Download HTML Report",
            report_html,
            file_name="report.html",
            mime="text/html",
            width="stretch",
        )
        figure_name = st.selectbox("Figure export", list(figures.keys()))
        selected_figure = figures[figure_name]
        st.download_button(
            "Download Figure HTML",
            figure_to_html_bytes(selected_figure),
            file_name=f"{figure_name.lower().replace(' ', '_')}.html",
            mime="text/html",
            width="stretch",
        )
        png_bytes = figure_to_png_bytes(selected_figure)
        if png_bytes is None:
            st.info("PNG export needs Plotly's Kaleido backend. HTML export is available now.")
        else:
            st.download_button(
                "Download Figure PNG",
                png_bytes,
                file_name=f"{figure_name.lower().replace(' ', '_')}.png",
                mime="image/png",
                width="stretch",
            )


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
            <p>Interactive 1D cycle model with explicit static vs total station data, actual vs theoretical plots, and exportable reports.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    config = _build_sidebar_config()
    result = run_engine_case(config)
    summary = summarize_result(result, V0=config["flight_speed"])
    station_df = result.to_dataframe()
    component_df = result.to_component_dataframe()

    figures = {
        "T-s Diagram": plot_TS(result, show=False, persist=False),
        "P-v Diagram": plot_PV(result, show=False, persist=False),
        "T-P Diagram": plot_TP(result, show=False, persist=False),
        "Performance": plot_performance(result, show=False, persist=False),
        "Engine Flow Actual": plot_engine_flow(result, ideal=False, show=False, persist=False),
        "Engine Flow Theoretical": plot_engine_flow(result, ideal=True, show=False, persist=False),
    }

    metrics = st.columns(6)
    with metrics[0]:
        _metric_card("Thrust", f"{summary['thrust_N']:.1f} N")
    with metrics[1]:
        _metric_card("Specific Thrust", f"{summary['specific_thrust_N_per_kg_s']:.1f}")
    with metrics[2]:
        _metric_card("Fuel-Air Ratio", f"{summary['fuel_air_ratio']:.5f}")
    with metrics[3]:
        _metric_card("Exit Mach", f"{summary['exit_mach']:.2f}")
    with metrics[4]:
        _metric_card("Overall Eff.", f"{summary['overall_efficiency']:.3f}")
    with metrics[5]:
        _metric_card("Nozzle Choked", "Yes" if summary["nozzle_choked"] else "No")

    st.caption(
        "Static quantities are local flow conditions. Total quantities are stagnation conditions obtained by bringing the flow to rest isentropically at that station."
    )

    tabs = st.tabs(["Cycle Plots", "Engine View", "Parametric Sweep", "Operating Map", "Stations", "Exports"])

    with tabs[0]:
        left, right = st.columns(2)
        left.plotly_chart(figures["T-s Diagram"], width="stretch")
        right.plotly_chart(figures["P-v Diagram"], width="stretch")
        left, right = st.columns(2)
        left.plotly_chart(figures["T-P Diagram"], width="stretch")
        right.plotly_chart(figures["Performance"], width="stretch")

    with tabs[1]:
        branch = st.radio("Schematic branch", ["Actual", "Theoretical"], horizontal=True)
        figure_key = "Engine Flow Theoretical" if branch == "Theoretical" else "Engine Flow Actual"
        st.plotly_chart(figures[figure_key], width="stretch")

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
        controls = st.columns(6)
        altitude_min = controls[0].slider("Alt min (m)", 0, 12000, 0, step=500)
        altitude_max = controls[1].slider("Alt max (m)", 2000, 15000, 10000, step=500)
        altitude_points = controls[2].slider("Alt points", 3, 8, 5)
        speed_min = controls[3].slider("Speed min (m/s)", 0, 250, 50, step=10)
        speed_max = controls[4].slider("Speed max (m/s)", 100, 450, 300, step=10)
        speed_points = controls[5].slider("Speed points", 3, 8, 5)
        metric = st.selectbox(
            "Map metric",
            ["thrust_N", "overall_efficiency", "specific_thrust_N_per_kg_s"],
            format_func=lambda key: {
                "thrust_N": "Thrust",
                "overall_efficiency": "Overall Efficiency",
                "specific_thrust_N_per_kg_s": "Specific Thrust",
            }[key],
        )
        if altitude_min >= altitude_max or speed_min >= speed_max:
            st.warning("Minimum values must be smaller than maximum values.")
        else:
            altitudes = [altitude_min + i * (altitude_max - altitude_min) / (altitude_points - 1) for i in range(altitude_points)]
            speeds = [speed_min + i * (speed_max - speed_min) / (speed_points - 1) for i in range(speed_points)]
            envelope_df = sweep_flight_envelope(config, altitudes, speeds)
            operating_map = plot_operating_map(envelope_df, metric=metric, show=False, persist=False)
            st.plotly_chart(operating_map, width="stretch")
            st.dataframe(envelope_df.round(4), width="stretch", hide_index=True)
            st.download_button(
                "Download Envelope CSV",
                envelope_df.to_csv(index=False).encode("utf-8"),
                file_name="operating_envelope.csv",
                mime="text/csv",
                width="stretch",
            )

    with tabs[4]:
        table_mode = st.radio("Table view", ["Combined", "Actual Focus", "Theoretical Focus", "Component Deltas"], horizontal=True)
        if table_mode == "Component Deltas":
            st.dataframe(component_df.round(4), width="stretch", hide_index=True)
        else:
            st.dataframe(_station_column_view(station_df.round(4), table_mode), width="stretch", hide_index=True)

    with tabs[5]:
        _download_buttons(figures, station_df.round(6), component_df.round(6), summary)


if __name__ == "__main__":
    main()
