import math
from pathlib import Path

import numpy as np
import plotly.figure_factory as ff
import plotly.graph_objects as go


SECTION_LAYOUT = {
    "Inlet": {"length": 1.25, "kind": "diffuser"},
    "Compressor": {"length": 1.45, "kind": "compressor"},
    "Combustor": {"length": 1.35, "kind": "combustor"},
    "Turbine": {"length": 1.25, "kind": "turbine"},
    "Afterburner": {"length": 1.20, "kind": "afterburner"},
    "Nozzle": {"length": 1.55, "kind": "nozzle"},
}
DEFAULT_SECTION = {"length": 1.20, "kind": "duct"}
HEAT_COLORSCALE = [
    [0.00, "#163A70"],
    [0.20, "#1F78B4"],
    [0.48, "#F2C14E"],
    [0.72, "#F28E2B"],
    [1.00, "#C44536"],
]
GRID_X = 560
GRID_Y = 180
FIELD_X = 24
FIELD_Y = 9
OUTPUT_DIR = Path("outputs")


def _finite_positive(*values):
    finite_values = [value for value in values if isinstance(value, (int, float)) and math.isfinite(value) and value > 0.0]
    return max(finite_values) if finite_values else 1e-6


def _state_value(state, field, ideal=False):
    if ideal:
        return getattr(state, f"{field}_ideal")
    return getattr(state, field)


def _station_payload(state, ideal=False):
    return {
        "label": state.stage_name or "Freestream",
        "T": _state_value(state, "T", ideal),
        "Tt": _state_value(state, "Tt", ideal),
        "P": _state_value(state, "P", ideal),
        "Pt": _state_value(state, "Pt", ideal),
        "V": _state_value(state, "V", ideal),
        "M": _state_value(state, "M", ideal),
        "area": _finite_positive(_state_value(state, "area", ideal), _state_value(state, "exit_area", ideal)),
        "m_dot": state.m_dot_ideal if ideal else state.m_dot_actual,
        "R": state.R,
    }


def _section_spec(stage_name):
    return SECTION_LAYOUT.get(stage_name, DEFAULT_SECTION)


def _height_from_area(area, reference_area):
    normalized = max(area / max(reference_area, 1e-9), 0.05)
    return 0.32 + 0.98 * math.sqrt(normalized)


def _build_sections(states, ideal=False):
    if hasattr(states, "states"):
        states = states.states

    payloads = [_station_payload(state, ideal) for state in states]
    reference_area = max(payload["area"] for payload in payloads)
    sections = []
    x_cursor = 0.0

    for index in range(1, len(states)):
        stage_name = states[index].stage_name or f"Stage {index}"
        spec = _section_spec(stage_name)
        start = payloads[index - 1]
        end = payloads[index]

        sections.append(
            {
                "name": stage_name,
                "kind": spec["kind"],
                "x0": x_cursor,
                "x1": x_cursor + spec["length"],
                "h0": _height_from_area(start["area"], reference_area),
                "h1": _height_from_area(end["area"], reference_area),
                "start": start,
                "end": end,
            }
        )
        x_cursor += spec["length"]

    return sections


def _station_locations(sections):
    positions = []
    if not sections:
        return positions

    positions.append({"x": sections[0]["x0"], "h": sections[0]["h0"], "station": sections[0]["start"]})
    for section in sections:
        positions.append({"x": section["x1"], "h": section["h1"], "station": section["end"]})
    return positions


def _density(temperature, pressure, gas_constant):
    return pressure / (gas_constant * temperature)


def _display_velocities(stations):
    velocities = []

    for station in stations:
        velocity = station["station"]["V"]
        if velocity > 1.0:
            velocities.append(velocity)
            continue

        rho = _density(station["station"]["T"], station["station"]["P"], station["station"]["R"])
        area = max(station["station"]["area"], 1e-6)
        velocities.append(station["station"]["m_dot"] / max(rho * area, 1e-9))

    return velocities


def _wall_shape(section, x_value):
    ratio = (x_value - section["x0"]) / (section["x1"] - section["x0"])
    return (1.0 - ratio) * section["h0"] + ratio * section["h1"]


def _locate_section(sections, x_value):
    for section in sections:
        if section["x0"] <= x_value <= section["x1"] + 1e-9:
            return section
    return sections[-1]


def _temperature_map(sections):
    total_length = sections[-1]["x1"]
    max_half_height = max(max(section["h0"], section["h1"]) for section in sections)
    x_values = np.linspace(0.0, total_length, GRID_X)
    y_values = np.linspace(-1.2 * max_half_height, 1.2 * max_half_height, GRID_Y)
    field = np.full((GRID_Y, GRID_X), np.nan)
    hover = np.full((GRID_Y, GRID_X), "", dtype=object)

    for column, x_value in enumerate(x_values):
        section = _locate_section(sections, x_value)
        ratio = (x_value - section["x0"]) / (section["x1"] - section["x0"])
        wall = _wall_shape(section, x_value)
        centerline_temperature = (1.0 - ratio) * section["start"]["T"] + ratio * section["end"]["T"]
        centerline_pressure = (1.0 - ratio) * section["start"]["P"] + ratio * section["end"]["P"]
        centerline_total_pressure = (1.0 - ratio) * section["start"]["Pt"] + ratio * section["end"]["Pt"]

        for row, y_value in enumerate(y_values):
            if abs(y_value) <= wall:
                radial_ratio = abs(y_value) / max(wall, 1e-9)
                wall_cooling = 1.0 - 0.18 * radial_ratio**1.3
                temperature = centerline_temperature * wall_cooling
                field[row, column] = temperature
                hover[row, column] = (
                    f"<b>{section['name']}</b><br>"
                    f"Temperature: {temperature:.1f} K<br>"
                    f"Approx. pressure: {centerline_pressure / 1000.0:.1f} kPa<br>"
                    f"Approx. total pressure: {centerline_total_pressure / 1000.0:.1f} kPa<br>"
                    f"Relative height: {y_value:.2f}"
                )

    return x_values, y_values, field, hover


def _velocity_field(sections, stations, velocities):
    max_half_height = max(max(section["h0"], section["h1"]) for section in sections)
    x_points = np.linspace(sections[0]["x0"] + 0.12, sections[-1]["x1"] - 0.16, FIELD_X)
    y_points = np.linspace(-0.88 * max_half_height, 0.88 * max_half_height, FIELD_Y)
    vmax = max(velocities) if velocities else 1.0

    xs = []
    ys = []
    us = []
    vs = []

    for x_value in x_points:
        section = _locate_section(sections, x_value)
        wall = _wall_shape(section, x_value)
        section_index = sections.index(section)
        section_ratio = (x_value - section["x0"]) / (section["x1"] - section["x0"])
        local_velocity = (1.0 - section_ratio) * velocities[section_index] + section_ratio * velocities[section_index + 1]
        normalized_velocity = local_velocity / max(vmax, 1e-9)
        wall_slope = (section["h1"] - section["h0"]) / (section["x1"] - section["x0"])

        for y_value in y_points:
            if abs(y_value) <= 0.86 * wall:
                radial_ratio = y_value / max(wall, 1e-9)
                xs.append(x_value)
                ys.append(y_value)
                us.append(0.12 + 0.24 * normalized_velocity)
                vs.append(-0.06 * wall_slope * radial_ratio)

    return xs, ys, us, vs


def _outline_traces(sections):
    traces = []

    for section in sections:
        x_values = np.linspace(section["x0"], section["x1"], 36)
        top = [_wall_shape(section, x) for x in x_values]
        bottom = [-value for value in top]
        line_style = {"color": "#102A43", "width": 3}

        traces.append(go.Scatter(x=x_values, y=top, mode="lines", line=line_style, hoverinfo="skip", showlegend=False))
        traces.append(go.Scatter(x=x_values, y=bottom, mode="lines", line=line_style, hoverinfo="skip", showlegend=False))
        traces.append(
            go.Scatter(
                x=[section["x0"], section["x0"]],
                y=[-section["h0"], section["h0"]],
                mode="lines",
                line={"color": "#102A43", "width": 1.5},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    last = sections[-1]
    traces.append(
        go.Scatter(
            x=[last["x1"], last["x1"]],
            y=[-last["h1"], last["h1"]],
            mode="lines",
            line={"color": "#102A43", "width": 1.5},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    return traces


def _pattern_traces(sections):
    traces = []

    for section in sections:
        x0 = section["x0"]
        x1 = section["x1"]
        local_height = 0.5 * (section["h0"] + section["h1"])

        if section["kind"] == "compressor":
            blade_positions = np.linspace(x0 + 0.18, x1 - 0.18, 5)
            for blade_x in blade_positions:
                traces.append(
                    go.Scatter(
                        x=[blade_x - 0.05, blade_x + 0.05],
                        y=[-0.45 * local_height, 0.45 * local_height],
                        mode="lines",
                        line={"color": "rgba(16,42,67,0.45)", "width": 2},
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )
        elif section["kind"] == "turbine":
            blade_positions = np.linspace(x0 + 0.18, x1 - 0.18, 5)
            for blade_x in blade_positions:
                traces.append(
                    go.Scatter(
                        x=[blade_x - 0.05, blade_x + 0.05],
                        y=[0.45 * local_height, -0.45 * local_height],
                        mode="lines",
                        line={"color": "rgba(16,42,67,0.45)", "width": 2},
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )
        elif section["kind"] in {"combustor", "afterburner"}:
            flame_x = np.linspace(x0 + 0.22, x1 - 0.22, 8)
            flame_y = 0.18 * local_height * np.sin(np.linspace(0.0, 2.8 * math.pi, len(flame_x)))
            traces.append(
                go.Scatter(
                    x=flame_x,
                    y=flame_y,
                    mode="lines",
                    line={"color": "#C44536", "width": 3},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    return traces


def _annotations(sections, velocities, ideal=False):
    annotations = []

    for index, section in enumerate(sections):
        x_mid = 0.5 * (section["x0"] + section["x1"])
        y_text = max(section["h0"], section["h1"]) + 0.24
        outlet = section["end"]
        local_velocity = velocities[index + 1]
        branch = "Theoretical" if ideal else "Actual"

        annotations.append(
            {
                "x": x_mid,
                "y": y_text,
                "xref": "x",
                "yref": "y",
                "showarrow": False,
                "align": "center",
                "font": {"size": 10, "color": "#102A43"},
                "text": (
                    f"<b>{section['name']}</b><br>"
                    f"{branch} outlet<br>"
                    f"T = {outlet['T']:.0f} K, Tt = {outlet['Tt']:.0f} K<br>"
                    f"P = {outlet['P'] / 1000:.0f} kPa, Pt = {outlet['Pt'] / 1000:.0f} kPa<br>"
                    f"V ~ {local_velocity:.0f} m/s, M = {outlet['M']:.2f}<br>"
                    f"A = {outlet['area']:.3f} m^2"
                ),
            }
        )

    annotations.append(
        {
            "x": 0.02,
            "y": 1.12,
            "xref": "paper",
            "yref": "paper",
            "showarrow": False,
            "align": "left",
            "font": {"size": 11, "color": "#486581"},
            "text": "Schematic 1D thermal-flow field. Colors represent static temperature, arrows indicate approximate flow field.",
        }
    )
    return annotations


def plot_engine_flow(states, ideal=False, show=True, persist=True):
    sections = _build_sections(states, ideal=ideal)
    if not sections:
        raise ValueError("At least one processed engine section is required.")

    stations = _station_locations(sections)
    velocities = _display_velocities(stations)
    x_values, y_values, field, hover = _temperature_map(sections)
    qx, qy, qu, qv = _velocity_field(sections, stations, velocities)

    fig = go.Figure()
    fig.add_trace(
        go.Heatmap(
            x=x_values,
            y=y_values,
            z=field,
            colorscale=HEAT_COLORSCALE,
            colorbar={"title": "Static<br>Temperature (K)"},
            hoverinfo="text",
            text=hover,
            hoverongaps=False,
            showscale=True,
            zsmooth="best",
            name="Temperature field",
        )
    )

    quiver = ff.create_quiver(
        qx,
        qy,
        qu,
        qv,
        scale=1.0,
        arrow_scale=0.28,
        line={"color": "rgba(255,255,255,0.82)", "width": 1.4},
        name="Flow field",
    )
    for trace in quiver.data:
        trace.showlegend = False
        trace.hoverinfo = "skip"
        fig.add_trace(trace)

    for trace in _outline_traces(sections):
        fig.add_trace(trace)
    for trace in _pattern_traces(sections):
        fig.add_trace(trace)

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#F6F8FB",
        plot_bgcolor="#EEF3F8",
        title={
            "text": f"{'Theoretical' if ideal else 'Actual'} Engine Thermal-Flow Schematic",
            "x": 0.04,
        },
        margin={"l": 40, "r": 40, "t": 86, "b": 46},
        font={"family": "Arial", "size": 13, "color": "#102A43"},
        annotations=_annotations(sections, velocities, ideal=ideal),
    )
    fig.update_xaxes(
        title="Engine Axis",
        showgrid=False,
        zeroline=False,
        showticklabels=False,
    )
    fig.update_yaxes(
        title="Relative Duct Height",
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        scaleanchor="x",
        scaleratio=1,
    )

    if persist:
        OUTPUT_DIR.mkdir(exist_ok=True)
        filename = "engine_flow_ideal.html" if ideal else "engine_flow_actual.html"
        output_path = OUTPUT_DIR / filename
        fig.write_html(output_path, include_plotlyjs=True, full_html=True, auto_open=show)
        print(f"Saved plot: {output_path.resolve()}")
    elif show:
        fig.show()
    return fig
