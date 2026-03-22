from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from configs.default import get_default_config
from performance.metrics import summarize_result
from performance.reporting import build_html_report
from solver.engine import run_engine_case, sweep_parameter
from visualization.plots import (
    figure_to_html_bytes,
    plot_PV,
    plot_TP,
    plot_TS,
    plot_engine_flow,
    plot_performance,
)


SUMMARY_KEYS = [
    "thrust_N",
    "specific_thrust_N_per_kg_s",
    "fuel_air_ratio",
    "fuel_flow_kg_s",
    "specific_impulse_s",
    "compressor_work_J_per_kg",
    "turbine_work_J_per_kg",
    "heat_input_J_per_kg",
    "bwr",
    "thermal_efficiency",
    "propulsive_efficiency",
    "overall_efficiency",
    "exit_velocity_mps",
    "exit_mach",
    "exit_area_m2",
    "nozzle_choked",
    "feasible",
]

COMPARISON_KEYS = [
    "thrust_N",
    "specific_thrust_N_per_kg_s",
    "fuel_air_ratio",
    "fuel_flow_kg_s",
    "specific_impulse_s",
    "thermal_efficiency",
    "propulsive_efficiency",
    "overall_efficiency",
    "bwr",
    "exit_velocity_mps",
]

SWEEP_OPTIONS = {
    "Compressor Pressure Ratio": "compressor_pressure_ratio",
    "Turbine Inlet Temperature": "turbine_inlet_temperature",
    "Compressor Efficiency": "compressor_efficiency",
    "Turbine Efficiency": "turbine_efficiency",
    "Flight Speed": "flight_speed",
    "Altitude": "altitude_m",
}

SWEEP_LABELS = {
    "compressor_pressure_ratio": "Compressor pressure ratio",
    "turbine_inlet_temperature": "Turbine inlet temperature",
    "compressor_efficiency": "Compressor efficiency",
    "turbine_efficiency": "Turbine efficiency",
    "flight_speed": "Flight speed",
    "altitude_m": "Altitude",
}

METRIC_HELP = {
    "thrust": "F = m_dot_a[(1 + f)Ve - V0] + (Pe - P0)Ae",
    "thermal": "eta_th = {0.5[(1 + f)Ve^2 - V0^2]} / q_in",
    "overall": "eta_o = FV0 / (m_dot_a q_in) = eta_th eta_p",
    "isp": "Isp = F / (m_dot_f g0)",
    "fuel_air": "f = cp(Tt3 - Tt2) / (eta_b LHV)",
}

METRIC_LATEX = {
    "Thrust": r"F = \dot{m}_a[(1+f)V_e - V_0] + (P_e - P_0)A_e",
    "Specific thrust": r"\frac{F}{\dot{m}_a}",
    "Fuel-air ratio": r"f = \frac{c_p(T_{t,3} - T_{t,2})}{\eta_b \, LHV}",
    "Fuel flow": r"\dot{m}_f = f \, \dot{m}_a",
    "Specific impulse": r"I_{sp} = \frac{F}{\dot{m}_f g_0}",
    "Back work ratio": r"\mathrm{BWR} = \frac{w_c}{w_t}",
    "Thermal efficiency": r"\eta_{th} = \frac{\frac{1}{2}[(1+f)V_e^2 - V_0^2]}{q_{in}}",
    "Propulsive efficiency": r"\eta_p = \frac{F V_0}{\dot{m}_a \, \frac{1}{2}[(1+f)V_e^2 - V_0^2]}",
    "Overall efficiency": r"\eta_o = \frac{F V_0}{\dot{m}_a q_{in}} = \eta_{th}\eta_p",
}


def _linspace(start: float, end: float, count: int) -> list[float]:
    if count <= 1:
        return [float(start)]
    step = (end - start) / (count - 1)
    return [float(start + index * step) for index in range(count)]


def _build_sidebar_config() -> tuple[dict, bool]:
    defaults = get_default_config()
    config = dict(defaults)

    st.sidebar.header("Cycle Inputs")
    config["flight_input_mode"] = st.sidebar.radio(
        "Flight Input",
        ["speed", "mach"],
        index=0 if defaults["flight_input_mode"] == "speed" else 1,
        horizontal=True,
    )
    config["altitude_m"] = float(st.sidebar.slider("Altitude (m)", 0, 15000, int(defaults["altitude_m"]), step=250))
    if config["flight_input_mode"] == "speed":
        config["flight_speed"] = float(
            st.sidebar.slider("Flight Speed (m/s)", 0.0, 400.0, float(defaults["flight_speed"]), step=5.0)
        )
    else:
        config["flight_mach_number"] = float(
            st.sidebar.slider("Flight Mach", 0.0, 2.0, float(defaults["flight_mach_number"]), step=0.02)
        )

    config["mass_flow_rate"] = float(
        st.sidebar.slider("Air Mass Flow Rate (kg/s)", 1.0, 40.0, float(defaults["mass_flow_rate"]), step=1.0)
    )

    with st.sidebar.expander("Component Performance", expanded=True):
        config["pressure_recovery"] = float(
            st.slider("Inlet Pressure Recovery", 0.85, 1.0, float(defaults["pressure_recovery"]), step=0.01)
        )
        config["compressor_pressure_ratio"] = float(
            st.slider("Compressor Pressure Ratio", 1.0, 20.0, float(defaults["compressor_pressure_ratio"]), step=0.5)
        )
        config["compressor_efficiency"] = float(
            st.slider("Compressor Efficiency", 0.70, 0.98, float(defaults["compressor_efficiency"]), step=0.01)
        )
        config["turbine_inlet_temperature"] = float(
            st.slider("Turbine Inlet Temperature (K)", 900.0, 1800.0, float(defaults["turbine_inlet_temperature"]), step=25.0)
        )
        config["combustor_pressure_loss"] = float(
            st.slider("Combustor Pressure Loss", 0.0, 0.12, float(defaults["combustor_pressure_loss"]), step=0.005)
        )
        config["combustor_efficiency"] = float(
            st.slider("Combustor Efficiency", 0.90, 1.0, float(defaults["combustor_efficiency"]), step=0.005)
        )
        config["turbine_efficiency"] = float(
            st.slider("Turbine Efficiency", 0.75, 0.98, float(defaults["turbine_efficiency"]), step=0.01)
        )
        config["mechanical_efficiency"] = float(
            st.slider("Mechanical Efficiency", 0.85, 1.0, float(defaults["mechanical_efficiency"]), step=0.01)
        )
        config["nozzle_efficiency"] = float(
            st.slider("Nozzle Efficiency", 0.85, 1.0, float(defaults["nozzle_efficiency"]), step=0.01)
        )

    with st.sidebar.expander("Gas Properties", expanded=False):
        config["gas_cp"] = float(
            st.number_input("cp (J/kg-K)", min_value=500.0, value=float(defaults["gas_cp"]), step=10.0)
        )
        config["gas_gamma"] = float(
            st.number_input("gamma", min_value=1.05, value=float(defaults["gas_gamma"]), step=0.01)
        )
        config["fuel_lower_heating_value"] = float(
            st.number_input(
                "Fuel LHV (J/kg)",
                min_value=1_000_000.0,
                value=float(defaults["fuel_lower_heating_value"]),
                step=100_000.0,
            )
        )

    compare_mode = st.sidebar.checkbox("Compare Mode", value=False)
    config["ambient_temperature"] = None
    config["ambient_pressure"] = None
    config["verbose"] = False
    return config, compare_mode


def _build_compare_config(base_config: dict) -> dict:
    defaults = dict(base_config)
    defaults["compressor_pressure_ratio"] = min(defaults["compressor_pressure_ratio"] + 2.0, 20.0)
    defaults["turbine_inlet_temperature"] = min(defaults["turbine_inlet_temperature"] + 100.0, 1800.0)
    defaults["compressor_efficiency"] = max(defaults["compressor_efficiency"] - 0.03, 0.70)

    config = dict(defaults)
    st.caption("Case A uses the sidebar inputs. Configure Case B below.")

    top = st.columns(4)
    config["flight_input_mode"] = top[0].radio(
        "Case B Flight Input",
        ["speed", "mach"],
        index=0 if defaults["flight_input_mode"] == "speed" else 1,
        horizontal=True,
        key="compare_flight_mode",
    )
    config["altitude_m"] = float(
        top[1].number_input("Case B Altitude (m)", min_value=0.0, value=float(defaults["altitude_m"]), step=250.0)
    )
    if config["flight_input_mode"] == "speed":
        config["flight_speed"] = float(
            top[2].number_input("Case B Flight Speed (m/s)", min_value=0.0, value=float(defaults["flight_speed"]), step=5.0)
        )
    else:
        config["flight_mach_number"] = float(
            top[2].number_input("Case B Flight Mach", min_value=0.0, value=float(defaults["flight_mach_number"]), step=0.02)
        )
    config["mass_flow_rate"] = float(
        top[3].number_input("Case B Air Mass Flow (kg/s)", min_value=1.0, value=float(defaults["mass_flow_rate"]), step=1.0)
    )

    with st.expander("Case B Component Performance", expanded=True):
        row1 = st.columns(3)
        config["pressure_recovery"] = float(
            row1[0].number_input("Pressure Recovery", min_value=0.85, max_value=1.0, value=float(defaults["pressure_recovery"]), step=0.01)
        )
        config["compressor_pressure_ratio"] = float(
            row1[1].number_input("Compressor Pressure Ratio", min_value=1.0, max_value=20.0, value=float(defaults["compressor_pressure_ratio"]), step=0.5)
        )
        config["compressor_efficiency"] = float(
            row1[2].number_input("Compressor Efficiency", min_value=0.70, max_value=0.98, value=float(defaults["compressor_efficiency"]), step=0.01)
        )

        row2 = st.columns(3)
        config["turbine_inlet_temperature"] = float(
            row2[0].number_input("Turbine Inlet Temperature (K)", min_value=900.0, max_value=1800.0, value=float(defaults["turbine_inlet_temperature"]), step=25.0)
        )
        config["combustor_pressure_loss"] = float(
            row2[1].number_input("Combustor Pressure Loss", min_value=0.0, max_value=0.12, value=float(defaults["combustor_pressure_loss"]), step=0.005)
        )
        config["combustor_efficiency"] = float(
            row2[2].number_input("Combustor Efficiency", min_value=0.90, max_value=1.0, value=float(defaults["combustor_efficiency"]), step=0.005)
        )

        row3 = st.columns(2)
        config["turbine_efficiency"] = float(
            row3[0].number_input("Turbine Efficiency", min_value=0.75, max_value=0.98, value=float(defaults["turbine_efficiency"]), step=0.01)
        )
        config["mechanical_efficiency"] = float(
            row3[1].number_input("Mechanical Efficiency", min_value=0.85, max_value=1.0, value=float(defaults["mechanical_efficiency"]), step=0.01)
        )
        config["nozzle_efficiency"] = float(
            st.number_input("Nozzle Efficiency", min_value=0.85, max_value=1.0, value=float(defaults["nozzle_efficiency"]), step=0.01)
        )

    with st.expander("Case B Gas Properties", expanded=False):
        gas_row = st.columns(3)
        config["gas_cp"] = float(
            gas_row[0].number_input("cp (J/kg-K)", min_value=500.0, value=float(defaults["gas_cp"]), step=10.0, key="compare_cp")
        )
        config["gas_gamma"] = float(
            gas_row[1].number_input("gamma", min_value=1.05, value=float(defaults["gas_gamma"]), step=0.01, key="compare_gamma")
        )
        config["fuel_lower_heating_value"] = float(
            gas_row[2].number_input(
                "Fuel LHV (J/kg)",
                min_value=1_000_000.0,
                value=float(defaults["fuel_lower_heating_value"]),
                step=100_000.0,
                key="compare_lhv",
            )
        )

    config["ambient_temperature"] = None
    config["ambient_pressure"] = None
    config["verbose"] = False
    return config


def _summary_table(summary: dict) -> pd.DataFrame:
    rows = [{"Metric": key, "Value": summary[key]} for key in SUMMARY_KEYS if key in summary]
    return pd.DataFrame(rows)


def _course_notes(summary: dict) -> list[str]:
    notes = []
    if summary["bwr"] > 0.55:
        notes.append("Back work ratio is relatively high, so much of the turbine work is spent driving the compressor.")
    else:
        notes.append("Back work ratio is moderate, so the compressor does not dominate the cycle work balance.")

    if summary["thermal_efficiency"] > 0.35:
        notes.append("Thermal efficiency is comparatively strong for a basic Brayton-cycle calculation.")
    else:
        notes.append("Thermal efficiency is modest, which is common at lower pressure ratios or weaker component efficiencies.")

    if summary["nozzle_choked"]:
        notes.append("The nozzle is choked, so the exit reaches sonic conditions and pressure thrust contributes to net thrust.")
    else:
        notes.append("The nozzle is not choked, so the exit pressure relaxes directly toward ambient.")
    return notes


def _comparison_table(case_a: dict, case_b: dict) -> pd.DataFrame:
    rows = []
    for key in COMPARISON_KEYS:
        value_a = case_a.get(key)
        value_b = case_b.get(key)
        delta = value_b - value_a if isinstance(value_a, (int, float)) and isinstance(value_b, (int, float)) else "n/a"
        percent_delta = (
            100.0 * delta / value_a
            if isinstance(delta, (int, float)) and isinstance(value_a, (int, float)) and abs(value_a) > 1e-12
            else "n/a"
        )
        rows.append(
            {
                "metric": key,
                "case_a": value_a,
                "case_b": value_b,
                "delta_b_minus_a": delta,
                "percent_delta": percent_delta,
            }
        )
    return pd.DataFrame(rows)


def _sweep_plot(sweep_df: pd.DataFrame, parameter: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sweep_df[parameter],
            y=sweep_df["thrust_N"],
            mode="lines+markers",
            name="Thrust (N)",
            line={"color": "#0F6CBD", "width": 3},
            yaxis="y1",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sweep_df[parameter],
            y=sweep_df["overall_efficiency"],
            mode="lines+markers",
            name="Overall Efficiency",
            line={"color": "#C44536", "width": 3},
            yaxis="y2",
        )
    )
    fig.update_layout(
        template="plotly_white",
        title={"text": f"Parameter Sweep: {parameter}", "x": 0.04},
        paper_bgcolor="#F6F8FB",
        plot_bgcolor="#FFFFFF",
        font={"family": "Arial", "size": 13, "color": "#102A43"},
        margin={"l": 72, "r": 72, "t": 72, "b": 62},
        yaxis={"title": "Thrust (N)"},
        yaxis2={"title": "Overall Efficiency", "overlaying": "y", "side": "right"},
        legend={"orientation": "h", "y": 1.02, "x": 1.0, "xanchor": "right"},
    )
    fig.update_xaxes(title=parameter, gridcolor="#D9E2EC")
    return fig


def _render_sweep_docs(current_config: dict, parameter: str, start_value: float, end_value: float, count: int) -> None:
    with st.expander("How To Use The Sweep Tab", expanded=False):
        st.markdown(
            "Use this tab for a one-at-a-time parameter study. The app generates a set of evenly spaced values "
            "between your selected `Start` and `End`, then solves the full Brayton cycle separately at each point."
        )
        st.markdown("**Recommended workflow**")
        st.markdown(
            "1. Set up your baseline case in the sidebar.\n"
            "2. Choose one variable to study in the Sweep tab.\n"
            "3. Enter a physically reasonable start, end, and number of points.\n"
            "4. Read the plot as a trend study, not as a single design point."
        )

        st.markdown("**Calculation Basis**")
        st.write(
            "For each sweep value, the solver keeps all other current inputs fixed and reruns the full cycle model. "
            "This is not interpolation and it is not a curve fit. Every point is an independent thermodynamic solution."
        )
        st.latex(r"x_i = x_{\min} + \frac{i}{N-1}(x_{\max} - x_{\min}), \quad i = 0,1,\dots,N-1")
        st.latex(
            r"\text{Case}_i = \text{run\_engine\_case}\left(\text{baseline config with } "
            + SWEEP_LABELS[parameter].replace(" ", r"\ ")
            + r" = x_i\right)"
        )
        st.latex(r"F_i = \dot{m}_a[(1+f_i)V_{e,i} - V_0] + (P_{e,i} - P_0)A_{e,i}")
        st.latex(r"\eta_{o,i} = \frac{F_i V_0}{\dot{m}_a q_{in,i}}")

        st.markdown("**What the plot shows**")
        st.markdown(
            "- The blue curve is thrust for each solved case.\n"
            "- The red curve is overall efficiency for each solved case.\n"
            "- The table below the chart contains the exact solved values for every point."
        )

        st.markdown("**Important assumptions**")
        st.markdown(
            "- Only one variable is changed at a time.\n"
            "- The Brayton-cycle model uses constant gas properties and the current sidebar settings for all non-swept inputs.\n"
            "- If you sweep altitude, the ambient temperature and pressure are recalculated from the ISA atmosphere model at each altitude."
        )
        if parameter == "flight_speed":
            st.info(
                "Flight-speed sweep points are solved in direct speed mode. This avoids Mach-mode preprocessing from overwriting the sampled speed values."
            )

        st.caption(
            f"Current sweep setup: {SWEEP_LABELS[parameter]} from {start_value:.4g} to {end_value:.4g} using {count} points."
        )


def _figure_pack(result):
    return {
        "T-s Diagram": plot_TS(result, show=False, persist=False),
        "P-v Diagram": plot_PV(result, show=False, persist=False),
        "T-P Diagram": plot_TP(result, show=False, persist=False),
        "Performance": plot_performance(result, show=False, persist=False),
        "Actual Schematic": plot_engine_flow(result, ideal=False, show=False, persist=False),
        "Theoretical Schematic": plot_engine_flow(result, ideal=True, show=False, persist=False),
    }


def _render_metric_equations():
    with st.expander("Metric Equations", expanded=False):
        for label, equation in METRIC_LATEX.items():
            st.markdown(f"**{label}**")
            st.latex(equation)


def main():
    st.set_page_config(
        page_title="Brayton Cycle Simulator",
        page_icon=":material/functions:",
        layout="wide",
    )

    config, compare_mode = _build_sidebar_config()
    result = run_engine_case(config)
    summary = summarize_result(result, V0=result.config["flight_speed"])
    figures = _figure_pack(result)

    st.title("Brayton Cycle Simulator")
    st.caption("Interactive thermodynamic analysis of a turbojet Brayton cycle.")

    if summary["warnings"]:
        for warning in summary["warnings"]:
            st.warning(warning)

    tabs = st.tabs(["Overview", "Diagrams", "Tables", "Sweep", "Compare", "Report"])

    with tabs[0]:
        row = st.columns(5)
        row[0].metric("Thrust", f"{summary['thrust_N']:.1f} N", help=METRIC_HELP["thrust"])
        row[1].metric(
            "Thermal Efficiency",
            f"{summary['thermal_efficiency']:.3f}",
            help=METRIC_HELP["thermal"],
        )
        row[2].metric(
            "Overall Efficiency",
            f"{summary['overall_efficiency']:.3f}",
            help=METRIC_HELP["overall"],
        )
        row[3].metric(
            "Specific Impulse",
            f"{summary['specific_impulse_s']:.1f} s",
            help=METRIC_HELP["isp"],
        )
        row[4].metric(
            "Fuel-Air Ratio",
            f"{summary['fuel_air_ratio']:.5f}",
            help=METRIC_HELP["fuel_air"],
        )

        st.subheader("Interpretation")
        for note in _course_notes(summary):
            st.write(f"- {note}")

        _render_metric_equations()

        st.subheader("Key Results")
        st.dataframe(_summary_table(summary), width="stretch", hide_index=True)

        with st.expander("Model Assumptions", expanded=False):
            for item in result.assumptions:
                st.write(f"- {item}")

    with tabs[1]:
        left, right = st.columns(2)
        left.plotly_chart(figures["T-s Diagram"], width="stretch", key="brayton_ts")
        right.plotly_chart(figures["P-v Diagram"], width="stretch", key="brayton_pv")
        left, right = st.columns(2)
        left.plotly_chart(figures["T-P Diagram"], width="stretch", key="brayton_tp")
        right.plotly_chart(figures["Performance"], width="stretch", key="brayton_perf")

        schematic_mode = st.radio("Schematic View", ["Actual", "Theoretical"], horizontal=True)
        schematic_key = "Actual Schematic" if schematic_mode == "Actual" else "Theoretical Schematic"
        st.plotly_chart(figures[schematic_key], width="stretch", key=f"schematic_{schematic_mode.lower()}")

    with tabs[2]:
        st.subheader("Station Table")
        st.dataframe(result.to_dataframe().round(6), width="stretch", hide_index=True)
        st.subheader("Component Table")
        st.dataframe(result.to_component_dataframe().round(6), width="stretch", hide_index=True)

    with tabs[3]:
        option_label = st.selectbox(
            "Sweep Parameter",
            list(SWEEP_OPTIONS.keys()),
            help="Choose one variable to vary while all other current inputs stay fixed.",
        )
        parameter = SWEEP_OPTIONS[option_label]
        default_ranges = {
            "compressor_pressure_ratio": (2.0, 16.0),
            "turbine_inlet_temperature": (1100.0, 1700.0),
            "compressor_efficiency": (0.72, 0.95),
            "turbine_efficiency": (0.78, 0.96),
            "flight_speed": (50.0, 320.0),
            "altitude_m": (0.0, 12000.0),
        }
        start_default, end_default = default_ranges[parameter]
        col1, col2, col3 = st.columns(3)
        start_value = float(
            col1.number_input("Start", value=float(start_default), help="Lower bound of the sweep range.")
        )
        end_value = float(
            col2.number_input("End", value=float(end_default), help="Upper bound of the sweep range.")
        )
        count = int(
            col3.number_input(
                "Points",
                min_value=2,
                max_value=25,
                value=7,
                step=1,
                help="Number of evenly spaced cases to solve between Start and End.",
            )
        )
        _render_sweep_docs(config, parameter, start_value, end_value, count)
        values = _linspace(start_value, end_value, count)
        sweep_df = sweep_parameter(config, parameter, values)
        st.plotly_chart(_sweep_plot(sweep_df, parameter), width="stretch", key=f"sweep_{parameter}")
        st.dataframe(sweep_df.round(6), width="stretch", hide_index=True)

    with tabs[4]:
        if compare_mode:
            compare_config = _build_compare_config(config)
            compare_result = run_engine_case(compare_config)
            compare_summary = summarize_result(compare_result, V0=compare_result.config["flight_speed"])

            metric_cols = st.columns(3)
            metric_cols[0].metric("Case A Thrust", f"{summary['thrust_N']:.1f} N")
            metric_cols[1].metric("Case B Thrust", f"{compare_summary['thrust_N']:.1f} N")
            metric_cols[2].metric("Delta", f"{compare_summary['thrust_N'] - summary['thrust_N']:.1f} N")

            st.dataframe(
                _comparison_table(summary, compare_summary).round(6),
                width="stretch",
                hide_index=True,
            )

            top = st.columns(2)
            top[0].markdown("**Case A: T-s Diagram**")
            top[0].plotly_chart(plot_TS(result, show=False, persist=False), width="stretch", key="compare_a_ts")
            top[1].markdown("**Case B: T-s Diagram**")
            top[1].plotly_chart(plot_TS(compare_result, show=False, persist=False), width="stretch", key="compare_b_ts")

            middle = st.columns(2)
            middle[0].markdown("**Case A: P-v Diagram**")
            middle[0].plotly_chart(plot_PV(result, show=False, persist=False), width="stretch", key="compare_a_pv")
            middle[1].markdown("**Case B: P-v Diagram**")
            middle[1].plotly_chart(plot_PV(compare_result, show=False, persist=False), width="stretch", key="compare_b_pv")

            bottom = st.columns(2)
            bottom[0].markdown("**Case A: Engine Schematic**")
            bottom[0].plotly_chart(
                plot_engine_flow(result, show=False, persist=False),
                width="stretch",
                key="compare_a_flow",
            )
            bottom[1].markdown("**Case B: Engine Schematic**")
            bottom[1].plotly_chart(
                plot_engine_flow(compare_result, show=False, persist=False),
                width="stretch",
                key="compare_b_flow",
            )
        else:
            st.info("Enable Compare Mode in the sidebar to compare the current case against a second input set.")

    with tabs[5]:
        report_html = build_html_report(
            summary,
            {},
            config=result.config,
            assumptions=result.assumptions,
            equations=result.equations,
        )
        st.download_button(
            "Download HTML Report",
            data=report_html.encode("utf-8"),
            file_name="brayton_cycle_report.html",
            mime="text/html",
        )
        st.download_button(
            "Download Station Table",
            data=result.to_dataframe().to_csv(index=False).encode("utf-8"),
            file_name="station_summary.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download Component Table",
            data=result.to_component_dataframe().to_csv(index=False).encode("utf-8"),
            file_name="component_summary.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download T-s Diagram HTML",
            data=figure_to_html_bytes(figures["T-s Diagram"]),
            file_name="ts_diagram.html",
            mime="text/html",
        )
        st.markdown("Preview")
        st.components.v1.html(report_html, height=640, scrolling=True)


if __name__ == "__main__":
    main()
