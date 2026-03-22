from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from configs.default import get_preset_config, list_presets
from performance.metrics import summarize_result
from performance.reporting import build_html_report
from solver.engine import run_engine_case, sweep_flight_envelope, sweep_parameter
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


def _load_json_config(uploaded_file) -> dict:
    if uploaded_file is None:
        return {}
    return json.loads(uploaded_file.getvalue().decode("utf-8"))


def _metric_card(label: str, value: str, help_text: str | None = None) -> None:
    st.metric(label, value, help=help_text)


def _optional_area_input(label: str, key_prefix: str, default_value):
    enabled = st.checkbox(f"Lock {label}", value=default_value is not None, key=f"{key_prefix}_enabled")
    if not enabled:
        return None
    value = 0.0 if default_value is None else float(default_value)
    return st.number_input(label, min_value=0.0, value=value, step=0.001, format="%.4f", key=f"{key_prefix}_value")


def _base_config_from_sidebar() -> dict:
    preset_name = st.sidebar.selectbox("Preset", list_presets(), index=0)
    uploaded = st.sidebar.file_uploader("Load Config JSON", type=["json"])
    defaults = get_preset_config(preset_name)
    defaults.update(_load_json_config(uploaded))
    defaults["preset_name"] = preset_name if uploaded is None else defaults.get("preset_name", preset_name)
    return defaults


def _build_sidebar_config() -> dict:
    defaults = _base_config_from_sidebar()
    st.sidebar.header("Configuration")
    config = dict(defaults)

    config["architecture"] = st.sidebar.selectbox(
        "Architecture",
        ["turbojet", "turbofan"],
        index=0 if defaults["architecture"] == "turbojet" else 1,
    )
    config["flight_input_mode"] = st.sidebar.radio(
        "Flight Input",
        ["speed", "mach"],
        index=0 if defaults["flight_input_mode"] == "speed" else 1,
        horizontal=True,
    )
    config["altitude_m"] = float(
        st.sidebar.slider("Altitude (m)", 0, 16000, int(defaults["altitude_m"]), step=250)
    )
    if config["flight_input_mode"] == "speed":
        config["flight_speed"] = st.sidebar.slider(
            "Flight Speed (m/s)",
            0.0,
            450.0,
            float(defaults["flight_speed"]),
            step=5.0,
        )
    else:
        config["flight_mach_number"] = st.sidebar.slider(
            "Flight Mach",
            0.0,
            2.5,
            float(defaults["flight_mach_number"]),
            step=0.02,
        )
    config["mass_flow_rate"] = st.sidebar.slider(
        "Total Air Mass Flow (kg/s)",
        1.0,
        150.0,
        float(defaults["mass_flow_rate"]),
        step=1.0,
    )

    with st.sidebar.expander("Core", expanded=True):
        config["pressure_recovery"] = st.slider("Inlet Pressure Recovery", 0.85, 1.0, float(defaults["pressure_recovery"]), step=0.01)
        config["compressor_pressure_ratio"] = st.slider(
            "Core Compressor Pressure Ratio",
            1.0,
            30.0,
            float(defaults["compressor_pressure_ratio"]),
            step=0.5,
        )
        config["compressor_efficiency"] = st.slider(
            "Core Compressor Efficiency",
            0.70,
            0.98,
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
            0.15,
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
            "Single-Spool Turbine Efficiency",
            0.75,
            0.98,
            float(defaults["turbine_efficiency"]),
            step=0.01,
        )
        config["mechanical_efficiency"] = st.slider(
            "Single-Spool Mechanical Efficiency",
            0.80,
            1.0,
            float(defaults["mechanical_efficiency"]),
            step=0.01,
        )

    with st.sidebar.expander("Turbofan", expanded=config["architecture"] == "turbofan"):
        disabled = config["architecture"] != "turbofan"
        config["bypass_ratio"] = st.slider(
            "Bypass Ratio",
            0.0,
            10.0,
            float(defaults["bypass_ratio"]),
            step=0.1,
            disabled=disabled,
        )
        config["fan_pressure_ratio"] = st.slider(
            "Fan Pressure Ratio",
            1.0,
            2.5,
            float(defaults["fan_pressure_ratio"]),
            step=0.05,
            disabled=disabled,
        )
        config["fan_efficiency"] = st.slider(
            "Fan Efficiency",
            0.75,
            0.98,
            float(defaults["fan_efficiency"]),
            step=0.01,
            disabled=disabled,
        )
        config["bypass_duct_pressure_loss"] = st.slider(
            "Bypass Duct Pressure Loss",
            0.0,
            0.10,
            float(defaults["bypass_duct_pressure_loss"]),
            step=0.005,
            disabled=disabled,
        )
        config["hp_turbine_efficiency"] = st.slider(
            "HP Turbine Efficiency",
            0.75,
            0.98,
            float(defaults["hp_turbine_efficiency"]),
            step=0.01,
            disabled=disabled,
        )
        config["lp_turbine_efficiency"] = st.slider(
            "LP Turbine Efficiency",
            0.75,
            0.98,
            float(defaults["lp_turbine_efficiency"]),
            step=0.01,
            disabled=disabled,
        )
        config["hp_mechanical_efficiency"] = st.slider(
            "HP Mechanical Efficiency",
            0.80,
            1.0,
            float(defaults["hp_mechanical_efficiency"]),
            step=0.01,
            disabled=disabled,
        )
        config["lp_mechanical_efficiency"] = st.slider(
            "LP Mechanical Efficiency",
            0.80,
            1.0,
            float(defaults["lp_mechanical_efficiency"]),
            step=0.01,
            disabled=disabled,
        )

    with st.sidebar.expander("Afterburner", expanded=False):
        config["afterburner_enabled"] = st.checkbox("Enable Afterburner", value=bool(defaults["afterburner_enabled"]))
        config["afterburner_exit_temperature"] = st.slider(
            "Afterburner Exit Temperature (K)",
            1100.0,
            2400.0,
            float(defaults["afterburner_exit_temperature"]),
            step=25.0,
            disabled=not config["afterburner_enabled"],
        )
        config["afterburner_pressure_loss"] = st.slider(
            "Afterburner Pressure Loss",
            0.0,
            0.12,
            float(defaults["afterburner_pressure_loss"]),
            step=0.005,
            disabled=not config["afterburner_enabled"],
        )
        config["afterburner_efficiency"] = st.slider(
            "Afterburner Efficiency",
            0.90,
            1.0,
            float(defaults["afterburner_efficiency"]),
            step=0.005,
            disabled=not config["afterburner_enabled"],
        )

    with st.sidebar.expander("Nozzles", expanded=False):
        config["core_nozzle_type"] = st.selectbox(
            "Core Nozzle Type",
            ["convergent", "converging-diverging"],
            index=0 if defaults["core_nozzle_type"] == "convergent" else 1,
        )
        config["nozzle_efficiency"] = st.slider(
            "Core Nozzle Efficiency",
            0.80,
            1.0,
            float(defaults["nozzle_efficiency"]),
            step=0.01,
        )
        config["core_nozzle_pressure_loss"] = st.slider(
            "Core Nozzle Pressure Loss",
            0.0,
            0.10,
            float(defaults["core_nozzle_pressure_loss"]),
            step=0.005,
        )
        config["core_nozzle_throat_area"] = _optional_area_input(
            "Core Throat Area (m^2)",
            "core_throat",
            defaults.get("core_nozzle_throat_area"),
        )
        config["core_nozzle_exit_area"] = _optional_area_input(
            "Core Exit Area (m^2)",
            "core_exit",
            defaults.get("core_nozzle_exit_area"),
        )
        config["bypass_nozzle_type"] = st.selectbox(
            "Bypass Nozzle Type",
            ["convergent", "converging-diverging"],
            index=0 if defaults["bypass_nozzle_type"] == "convergent" else 1,
            disabled=config["architecture"] != "turbofan",
        )
        config["bypass_nozzle_efficiency"] = st.slider(
            "Bypass Nozzle Efficiency",
            0.80,
            1.0,
            float(defaults["bypass_nozzle_efficiency"]),
            step=0.01,
            disabled=config["architecture"] != "turbofan",
        )
        config["bypass_nozzle_pressure_loss"] = st.slider(
            "Bypass Nozzle Pressure Loss",
            0.0,
            0.10,
            float(defaults["bypass_nozzle_pressure_loss"]),
            step=0.005,
            disabled=config["architecture"] != "turbofan",
        )
        config["bypass_nozzle_throat_area"] = _optional_area_input(
            "Bypass Throat Area (m^2)",
            "bypass_throat",
            defaults.get("bypass_nozzle_throat_area"),
        )
        config["bypass_nozzle_exit_area"] = _optional_area_input(
            "Bypass Exit Area (m^2)",
            "bypass_exit",
            defaults.get("bypass_nozzle_exit_area"),
        )

    with st.sidebar.expander("Gas Model", expanded=False):
        config["gas_temperature_dependent"] = st.checkbox(
            "Temperature-Dependent cp(T)",
            value=bool(defaults["gas_temperature_dependent"]),
        )
        config["gas_cp"] = st.number_input("cp_ref (J/kg-K)", value=float(defaults["gas_cp"]), step=5.0)
        config["gas_gamma"] = st.number_input("gamma_ref", value=float(defaults["gas_gamma"]), step=0.01)
        config["gas_cp_temperature_slope"] = st.number_input(
            "cp Slope (J/kg-K^2)",
            value=float(defaults["gas_cp_temperature_slope"]),
            step=0.01,
            format="%.3f",
            disabled=not config["gas_temperature_dependent"],
        )
        config["fuel_lower_heating_value"] = st.number_input(
            "Fuel LHV (J/kg)",
            value=float(defaults["fuel_lower_heating_value"]),
            step=500000.0,
            format="%.0f",
        )

    with st.sidebar.expander("Maps", expanded=False):
        config["component_maps_enabled"] = st.checkbox(
            "Enable Simple Component Maps",
            value=bool(defaults["component_maps_enabled"]),
        )
        config["map_sensitivity_pressure_ratio"] = st.slider(
            "PR Map Sensitivity",
            0.0,
            0.25,
            float(defaults["map_sensitivity_pressure_ratio"]),
            step=0.01,
            disabled=not config["component_maps_enabled"],
        )
        config["map_sensitivity_corrected_flow"] = st.slider(
            "Flow Map Sensitivity",
            0.0,
            0.25,
            float(defaults["map_sensitivity_corrected_flow"]),
            step=0.01,
            disabled=not config["component_maps_enabled"],
        )
        config["turbine_map_sensitivity_loading"] = st.slider(
            "Turbine Loading Sensitivity",
            0.0,
            0.25,
            float(defaults["turbine_map_sensitivity_loading"]),
            step=0.01,
            disabled=not config["component_maps_enabled"],
        )

    with st.sidebar.expander("Section Velocities", expanded=False):
        config["diffuser_exit_velocity"] = st.slider("Diffuser Exit Velocity (m/s)", 20.0, 220.0, float(defaults["diffuser_exit_velocity"]), step=5.0)
        config["fan_exit_velocity"] = st.slider("Fan Exit Velocity (m/s)", 40.0, 260.0, float(defaults["fan_exit_velocity"]), step=5.0)
        config["compressor_exit_velocity"] = st.slider("Core Compressor Exit Velocity (m/s)", 40.0, 260.0, float(defaults["compressor_exit_velocity"]), step=5.0)
        config["combustor_exit_velocity"] = st.slider("Combustor Exit Velocity (m/s)", 20.0, 180.0, float(defaults["combustor_exit_velocity"]), step=5.0)
        config["turbine_exit_velocity"] = st.slider("Turbine Exit Velocity (m/s)", 40.0, 280.0, float(defaults["turbine_exit_velocity"]), step=5.0)
        config["afterburner_exit_velocity"] = st.slider("Afterburner Exit Velocity (m/s)", 80.0, 320.0, float(defaults["afterburner_exit_velocity"]), step=5.0)

    config["verbose"] = False
    return config


def _figures_for_result(result):
    return {
        "T-s Diagram": plot_TS(result, show=False, persist=False),
        "P-v Diagram": plot_PV(result, show=False, persist=False),
        "T-P Diagram": plot_TP(result, show=False, persist=False),
        "Performance": plot_performance(result, show=False, persist=False),
        "Engine Flow Actual": plot_engine_flow(result, ideal=False, show=False, persist=False),
        "Engine Flow Theoretical": plot_engine_flow(result, ideal=True, show=False, persist=False),
    }


def _warning_panel(summary):
    if not summary["warnings"]:
        return
    with st.expander("Warnings", expanded=True):
        for warning in summary["warnings"]:
            st.warning(warning)
        if not summary["feasible"]:
            st.info("Infeasible means the requested mass flow, work balance, and nozzle geometry cannot all be satisfied at the same time in the current 1D model.")


def _compare_case(primary_config):
    st.subheader("Reference Comparison")
    compare_preset = st.selectbox("Compare Against", list_presets(), index=0, key="compare_preset")
    compare_config = get_preset_config(compare_preset)
    for key in ("altitude_m", "flight_input_mode", "flight_speed", "flight_mach_number"):
        compare_config[key] = primary_config.get(key)
    compare_config["verbose"] = False
    compare_result = run_engine_case(compare_config)
    compare_summary = summarize_result(compare_result, V0=compare_result.config["flight_speed"])
    return compare_result, compare_summary


def _station_column_view(station_df: pd.DataFrame, mode: str) -> pd.DataFrame:
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
                "core_air_mass_flow_kg_s",
                "bypass_air_mass_flow_kg_s",
                "fuel_air_ratio",
                "infeasible",
                "status_message",
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
                "fuel_air_ratio",
                "infeasible",
                "status_message",
            ]
        ]
    return station_df


def _comparison_table(primary_summary, secondary_summary):
    metrics = [
        "thrust_N",
        "specific_thrust_N_per_kg_s",
        "tsfc_kg_per_N_s",
        "specific_impulse_s",
        "overall_efficiency",
        "fuel_flow_kg_s",
        "core_thrust_N",
        "bypass_thrust_N",
    ]
    rows = []
    for metric in metrics:
        primary = primary_summary.get(metric, 0.0)
        secondary = secondary_summary.get(metric, 0.0)
        rows.append(
            {
                "metric": metric,
                "current": primary,
                "reference": secondary,
                "delta": primary - secondary,
            }
        )
    return pd.DataFrame(rows)


def _build_sweep(parameter_name: str, config: dict, value_min: float, value_max: float, count: int):
    if count < 2 or value_min >= value_max:
        return pd.DataFrame()
    values = [value_min + i * (value_max - value_min) / (count - 1) for i in range(count)]
    if parameter_name == "flight_mach_number":
        sweep_config = dict(config)
        sweep_config["flight_input_mode"] = "mach"
        return sweep_parameter(sweep_config, parameter_name, values)
    return sweep_parameter(config, parameter_name, values)


def _sweep_plot(sweep_df: pd.DataFrame, parameter_name: str):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sweep_df[parameter_name],
            y=sweep_df["thrust_N"],
            mode="lines+markers",
            name="Thrust (N)",
            line={"color": "#0F6CBD", "width": 3},
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sweep_df[parameter_name],
            y=sweep_df["tsfc_kg_per_N_s"],
            mode="lines+markers",
            name="TSFC",
            line={"color": "#C44536", "width": 3, "dash": "dash"},
            yaxis="y2",
        )
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#F6F8FB",
        plot_bgcolor="#FFFFFF",
        title={"text": f"Parameter Sweep: {parameter_name}", "x": 0.04},
        margin={"l": 60, "r": 60, "t": 70, "b": 50},
        xaxis={"title": parameter_name},
        yaxis={"title": "Thrust (N)", "gridcolor": "#D9E2EC"},
        yaxis2={"title": "TSFC (kg/N-s)", "overlaying": "y", "side": "right", "showgrid": False},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1.0},
    )
    return fig


def _download_buttons(figures, station_df, component_df, summary, config, assumptions, equations):
    report_html = build_html_report(
        summary,
        {
            "station_csv": Path("station_summary.csv"),
            "component_csv": Path("component_summary.csv"),
            "summary_json": Path("summary_metrics.json"),
            "config_json": Path("config_snapshot.json"),
        },
        config=config,
        assumptions=assumptions,
        equations=equations,
    ).encode("utf-8")

    left, right = st.columns(2)
    with left:
        st.download_button(
            "Download Config JSON",
            json.dumps(config, indent=2).encode("utf-8"),
            file_name="engine_config.json",
            mime="application/json",
            width="stretch",
        )
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
        figure_name = st.selectbox("Figure Export", list(figures.keys()))
        selected_figure = figures[figure_name]
        st.download_button(
            "Download Figure HTML",
            figure_to_html_bytes(selected_figure),
            file_name=f"{figure_name.lower().replace(' ', '_')}.html",
            mime="text/html",
            width="stretch",
        )
        png_bytes = figure_to_png_bytes(selected_figure)
        if png_bytes is not None:
            st.download_button(
                "Download Figure PNG",
                png_bytes,
                file_name=f"{figure_name.lower().replace(' ', '_')}.png",
                mime="image/png",
                width="stretch",
            )
        else:
            st.info("PNG export needs Plotly's Kaleido backend.")


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
            <p>Turbojet and turbofan cycle simulator with simple off-design maps, optional afterburning, dual-stream nozzles, compare mode, and exportable reports.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    config = _build_sidebar_config()
    try:
        result = run_engine_case(config)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    summary = summarize_result(result, V0=result.config["flight_speed"])
    station_df = result.to_dataframe()
    component_df = result.to_component_dataframe()
    figures = _figures_for_result(result)
    compare_mode = st.sidebar.toggle("Compare Mode", value=True)

    if not summary["feasible"]:
        st.error("This operating point is thermodynamically infeasible in the current 1D model.")
    _warning_panel(summary)

    metrics = st.columns(8)
    with metrics[0]:
        _metric_card("Thrust", f"{summary['thrust_N']:.1f} N")
    with metrics[1]:
        _metric_card("Core / Bypass", f"{summary['core_thrust_N']:.0f} / {summary['bypass_thrust_N']:.0f} N")
    with metrics[2]:
        _metric_card("TSFC", f"{summary['tsfc_kg_per_N_s']:.6f}")
    with metrics[3]:
        _metric_card("Isp", f"{summary['specific_impulse_s']:.1f} s")
    with metrics[4]:
        _metric_card("Fuel Flow", f"{summary['fuel_flow_kg_s']:.3f} kg/s")
    with metrics[5]:
        _metric_card("Overall Eff.", f"{summary['overall_efficiency']:.3f}")
    with metrics[6]:
        _metric_card("Flight", f"{result.config['flight_speed']:.0f} m/s")
    with metrics[7]:
        _metric_card("Architecture", summary["architecture"])

    tabs = st.tabs(["Cycle Plots", "Engine View", "Sweeps", "Operating Map", "Stations", "Compare", "Report", "Exports"])

    with tabs[0]:
        left, right = st.columns(2)
        left.plotly_chart(figures["T-s Diagram"], width="stretch", key="primary_ts")
        right.plotly_chart(figures["P-v Diagram"], width="stretch", key="primary_pv")
        left, right = st.columns(2)
        left.plotly_chart(figures["T-P Diagram"], width="stretch", key="primary_tp")
        right.plotly_chart(figures["Performance"], width="stretch", key="primary_performance")

    with tabs[1]:
        branch = st.radio("Schematic Branch", ["Actual", "Theoretical"], horizontal=True)
        key = "Engine Flow Theoretical" if branch == "Theoretical" else "Engine Flow Actual"
        st.plotly_chart(figures[key], width="stretch", key=f"engine_view_{branch.lower()}")
        st.dataframe(
            pd.DataFrame(
                [
                    {"metric": "Bypass Exit Velocity (m/s)", "value": summary["bypass_exit_velocity_mps"]},
                    {"metric": "Bypass Exit Mach", "value": summary["bypass_exit_mach"]},
                    {"metric": "Inlet Capture Diameter (m)", "value": summary["inlet_capture_diameter_m"]},
                    {"metric": "Core Nozzle Diameter (m)", "value": summary["core_nozzle_diameter_m"]},
                    {"metric": "Bypass Nozzle Diameter (m)", "value": summary["bypass_nozzle_diameter_m"]},
                ]
            ),
            width="stretch",
            hide_index=True,
        )

    with tabs[2]:
        parameter = st.selectbox(
            "Sweep Parameter",
            [
                "compressor_pressure_ratio",
                "turbine_inlet_temperature",
                "afterburner_exit_temperature",
                "flight_speed",
                "flight_mach_number",
                "mass_flow_rate",
            ],
        )
        sweep_cols = st.columns(3)
        sweep_min = sweep_cols[0].number_input("Min", value=4.0 if "pressure_ratio" in parameter else 0.2)
        sweep_max = sweep_cols[1].number_input("Max", value=20.0 if "pressure_ratio" in parameter else 2.0)
        sweep_count = sweep_cols[2].slider("Points", 4, 20, 8)
        sweep_df = _build_sweep(parameter, config, float(sweep_min), float(sweep_max), int(sweep_count))
        if sweep_df.empty:
            st.warning("Sweep bounds are invalid.")
        else:
            st.plotly_chart(_sweep_plot(sweep_df, parameter), width="stretch", key=f"sweep_{parameter}")
            st.dataframe(sweep_df.round(6), width="stretch", hide_index=True)

    with tabs[3]:
        controls = st.columns(6)
        altitude_min = controls[0].slider("Alt Min (m)", 0, 12000, 0, step=500)
        altitude_max = controls[1].slider("Alt Max (m)", 2000, 16000, 12000, step=500)
        altitude_points = controls[2].slider("Alt Points", 3, 8, 5)
        map_mode = controls[3].selectbox("Map Input", ["speed", "mach"])
        speed_min = controls[4].slider("Input Min", 0, 300, 50, step=10)
        speed_max = controls[5].slider("Input Max", 100, 450, 300, step=10)
        points = st.slider("Input Points", 3, 8, 5)
        metric = st.selectbox(
            "Map Metric",
            ["thrust_N", "overall_efficiency", "specific_thrust_N_per_kg_s", "tsfc_kg_per_N_s"],
        )
        if altitude_min >= altitude_max or speed_min >= speed_max:
            st.warning("Minimum values must be smaller than maximum values.")
        else:
            altitudes = [altitude_min + i * (altitude_max - altitude_min) / (altitude_points - 1) for i in range(altitude_points)]
            values = [speed_min + i * (speed_max - speed_min) / (points - 1) for i in range(points)]
            envelope_df = sweep_flight_envelope(config, altitudes, values, input_mode=map_mode)
            operating_map = plot_operating_map(envelope_df, metric=metric, show=False, persist=False)
            st.plotly_chart(operating_map, width="stretch", key=f"operating_map_{map_mode}_{metric}")
            st.dataframe(envelope_df.round(6), width="stretch", hide_index=True)

    with tabs[4]:
        table_mode = st.radio("Table View", ["Combined", "Actual Focus", "Theoretical Focus", "Component Deltas"], horizontal=True)
        if table_mode == "Component Deltas":
            st.dataframe(component_df.round(6), width="stretch", hide_index=True)
        else:
            st.dataframe(_station_column_view(station_df.round(6), table_mode), width="stretch", hide_index=True)

    with tabs[5]:
        if compare_mode:
            compare_result, compare_summary = _compare_case(config)
            st.dataframe(_comparison_table(summary, compare_summary).round(6), width="stretch", hide_index=True)
            compare_cols = st.columns(2)
            compare_cols[0].plotly_chart(
                plot_TS(compare_result, show=False, persist=False),
                width="stretch",
                key="compare_ts",
            )
            compare_cols[1].plotly_chart(
                plot_engine_flow(compare_result, show=False, persist=False),
                width="stretch",
                key="compare_engine_flow",
            )
        else:
            st.info("Enable Compare Mode in the sidebar to compare the current case against a preset reference.")

    with tabs[6]:
        st.subheader("Assumptions")
        for item in result.assumptions:
            st.write(f"- {item}")
        st.subheader("Key Relations")
        for item in result.equations:
            st.write(f"- {item}")
        with st.expander("Configuration Snapshot"):
            st.json(result.config)
        with st.expander("Summary Snapshot"):
            st.json(summary)

    with tabs[7]:
        _download_buttons(figures, station_df.round(6), component_df.round(6), summary, result.config, result.assumptions, result.equations)


if __name__ == "__main__":
    main()
