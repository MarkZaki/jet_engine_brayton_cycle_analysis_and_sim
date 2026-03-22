from pathlib import Path

import plotly.io as pio
import plotly.graph_objects as go

from visualization.diagrams import PV_diagram, TP_diagram, TS_diagram, performance_diagram
from visualization.flow import plot_engine_flow as plot_engine_flow_figure


PLOT_THEME = {
    "paper_bgcolor": "#F6F8FB",
    "plot_bgcolor": "#FFFFFF",
    "font_color": "#102A43",
    "gridcolor": "#D9E2EC",
    "actual_color": "#0F6CBD",
    "ideal_color": "#7B8794",
    "accent_color": "#C44536",
}
OUTPUT_DIR = Path("outputs")


def _finalize_figure(fig, filename, show, persist):
    if persist:
        OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = OUTPUT_DIR / filename
        fig.write_html(output_path, include_plotlyjs=True, full_html=True, auto_open=show)
        print(f"Saved plot: {output_path.resolve()}")
    elif show:
        fig.show()
    return fig


def figure_to_html_bytes(fig):
    return fig.to_html(include_plotlyjs=True, full_html=True).encode("utf-8")


def figure_to_png_bytes(fig):
    try:
        return pio.to_image(fig, format="png", width=1400, height=900, scale=2)
    except Exception:
        return None


def _apply_layout(fig, title, x_title, y_title):
    fig.update_layout(
        template="plotly_white",
        title={"text": title, "x": 0.04},
        paper_bgcolor=PLOT_THEME["paper_bgcolor"],
        plot_bgcolor=PLOT_THEME["plot_bgcolor"],
        font={"family": "Arial", "color": PLOT_THEME["font_color"], "size": 13},
        hoverlabel={"bgcolor": "#102A43", "font_color": "#FFFFFF"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1.0},
        margin={"l": 72, "r": 36, "t": 72, "b": 62},
    )
    fig.update_xaxes(
        title=x_title,
        showgrid=True,
        gridcolor=PLOT_THEME["gridcolor"],
        zeroline=False,
    )
    fig.update_yaxes(
        title=y_title,
        showgrid=True,
        gridcolor=PLOT_THEME["gridcolor"],
        zeroline=False,
    )
    return fig


def _add_station_markers(fig, stations, x_key, y_key, x_fmt, y_fmt, branch, color):
    hover_text = [
        (
            f"<b>{station['label']}</b><br>"
            f"{x_key}: {x_fmt(station[x_key])}<br>"
            f"{y_key}: {y_fmt(station[y_key])}<br>"
            f"Tt: {station.get('Tt', station.get('T', 0.0)):.1f} K<br>"
            f"Pt: {station.get('Pt', station.get('P', 0.0)) / 1000.0:.1f} kPa"
        )
        for station in stations
    ]
    fig.add_trace(
        go.Scatter(
            x=[station[x_key] for station in stations],
            y=[station[y_key] for station in stations],
            mode="markers+text",
            text=[station["label"] for station in stations],
            textposition="top center",
            textfont={"size": 10, "color": color},
            marker={
                "size": 8,
                "color": color,
                "line": {"width": 1.5, "color": "#FFFFFF"},
            },
            name=f"{branch} stations",
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_text,
        )
    )


def plot_PV(states, show=True, persist=True):
    data = PV_diagram(states)
    actual_v, actual_p, _, _ = zip(*data["actual"]["curve"])
    ideal_v, ideal_p, _, _ = zip(*data["ideal"]["curve"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ideal_v,
            y=ideal_p,
            mode="lines",
            name="Theoretical cycle",
            line={"color": PLOT_THEME["ideal_color"], "width": 3, "dash": "dash"},
            hovertemplate="v: %{x:.4f} m^3/kg<br>P: %{y:.0f} Pa<extra>Theoretical</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=actual_v,
            y=actual_p,
            mode="lines",
            name="Actual cycle",
            line={"color": PLOT_THEME["actual_color"], "width": 3},
            hovertemplate="v: %{x:.4f} m^3/kg<br>P: %{y:.0f} Pa<extra>Actual</extra>",
        )
    )

    _add_station_markers(
        fig,
        data["ideal"]["stations"],
        "v",
        "P",
        lambda value: f"{value:.4f} m^3/kg",
        lambda value: f"{value:.0f} Pa",
        "Theoretical",
        PLOT_THEME["ideal_color"],
    )
    _add_station_markers(
        fig,
        data["actual"]["stations"],
        "v",
        "P",
        lambda value: f"{value:.4f} m^3/kg",
        lambda value: f"{value:.0f} Pa",
        "Actual",
        PLOT_THEME["actual_color"],
    )

    _apply_layout(fig, "P-v Diagram", "Specific Volume (m^3/kg)", "Pressure (Pa)")
    return _finalize_figure(fig, "pv_diagram.html", show, persist)


def plot_TS(states, show=True, persist=True):
    data = TS_diagram(states)
    _, _, actual_s, actual_t = zip(*data["actual"]["curve"])
    _, _, ideal_s, ideal_t = zip(*data["ideal"]["curve"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ideal_s,
            y=ideal_t,
            mode="lines",
            name="Theoretical cycle",
            line={"color": PLOT_THEME["ideal_color"], "width": 3, "dash": "dash"},
            hovertemplate="s: %{x:.1f} J/kg-K<br>T: %{y:.1f} K<extra>Theoretical</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=actual_s,
            y=actual_t,
            mode="lines",
            name="Actual cycle",
            line={"color": PLOT_THEME["actual_color"], "width": 3},
            hovertemplate="s: %{x:.1f} J/kg-K<br>T: %{y:.1f} K<extra>Actual</extra>",
        )
    )

    _add_station_markers(
        fig,
        data["ideal"]["stations"],
        "s",
        "T",
        lambda value: f"{value:.1f} J/kg-K",
        lambda value: f"{value:.1f} K",
        "Theoretical",
        PLOT_THEME["ideal_color"],
    )
    _add_station_markers(
        fig,
        data["actual"]["stations"],
        "s",
        "T",
        lambda value: f"{value:.1f} J/kg-K",
        lambda value: f"{value:.1f} K",
        "Actual",
        PLOT_THEME["actual_color"],
    )

    _apply_layout(fig, "T-s Diagram", "Entropy (J/kg-K)", "Temperature (K)")
    return _finalize_figure(fig, "ts_diagram.html", show, persist)


def plot_TP(states, show=True, persist=True):
    data = TP_diagram(states)
    _, actual_p, _, actual_t = zip(*data["actual"]["curve"])
    _, ideal_p, _, ideal_t = zip(*data["ideal"]["curve"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ideal_p,
            y=ideal_t,
            mode="lines",
            name="Theoretical path",
            line={"color": PLOT_THEME["ideal_color"], "width": 3, "dash": "dash"},
            hovertemplate="P: %{x:.0f} Pa<br>T: %{y:.1f} K<extra>Theoretical</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=actual_p,
            y=actual_t,
            mode="lines",
            name="Actual path",
            line={"color": PLOT_THEME["actual_color"], "width": 3},
            hovertemplate="P: %{x:.0f} Pa<br>T: %{y:.1f} K<extra>Actual</extra>",
        )
    )

    _add_station_markers(
        fig,
        data["ideal"]["stations"],
        "P",
        "T",
        lambda value: f"{value:.0f} Pa",
        lambda value: f"{value:.1f} K",
        "Theoretical",
        PLOT_THEME["ideal_color"],
    )
    _add_station_markers(
        fig,
        data["actual"]["stations"],
        "P",
        "T",
        lambda value: f"{value:.0f} Pa",
        lambda value: f"{value:.1f} K",
        "Actual",
        PLOT_THEME["actual_color"],
    )

    _apply_layout(fig, "T-P Diagram", "Pressure (Pa)", "Temperature (K)")
    return _finalize_figure(fig, "tp_diagram.html", show, persist)


def plot_performance(states, show=True, persist=True):
    data = performance_diagram(states)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=data["stage_names"],
            y=data["ideal_net"],
            name="Theoretical net work",
            marker={"color": PLOT_THEME["ideal_color"]},
            text=[f"{value:.0f}" for value in data["ideal_net"]],
            textposition="outside",
            hovertemplate="Stage: %{x}<br>Net work: %{y:.1f} J/kg<extra>Theoretical</extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=data["stage_names"],
            y=data["actual_net"],
            name="Actual net work",
            marker={"color": PLOT_THEME["actual_color"]},
            text=[f"{value:.0f}" for value in data["actual_net"]],
            textposition="outside",
            hovertemplate="Stage: %{x}<br>Net work: %{y:.1f} J/kg<extra>Actual</extra>",
        )
    )

    _apply_layout(fig, "Stage Delta Specific Work", "Stage", "Specific Work (J/kg)")
    fig.update_layout(barmode="group")
    return _finalize_figure(fig, "performance.html", show, persist)


def plot_engine_flow(states, ideal=False, show=True, persist=True):
    return plot_engine_flow_figure(states, ideal=ideal, show=show, persist=persist)
