from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go


OUTPUT_DIR = Path("outputs")
BLOCK_COLORS = {
    "Inlet": "#7DB7E8",
    "Compressor": "#3E7CB1",
    "Combustor": "#F28E2B",
    "Turbine": "#A23B72",
    "Nozzle": "#4D9078",
}
BLOCK_TEXT_COLORS = {
    "Inlet": "#102A43",
    "Compressor": "#FFFFFF",
    "Combustor": "#102A43",
    "Turbine": "#FFFFFF",
    "Nozzle": "#FFFFFF",
}
PROCESS_NOTES = {
    "Inlet": "Diffusion / pressure recovery",
    "Compressor": "Work input",
    "Combustor": "Heat addition",
    "Turbine": "Work output",
    "Nozzle": "Expansion to exhaust",
}


def _state_fields(state, ideal=False):
    prefix = "_ideal" if ideal else ""
    return {
        "T": getattr(state, f"T{prefix}"),
        "Tt": getattr(state, f"Tt{prefix}"),
        "P": getattr(state, f"P{prefix}"),
        "Pt": getattr(state, f"Pt{prefix}"),
        "V": getattr(state, f"V{prefix}"),
        "M": getattr(state, f"M{prefix}"),
        "A": getattr(state, f"exit_area{prefix}", 0.0) if (state.stage_name or "") == "Nozzle" else getattr(state, f"area{prefix}"),
    }


def plot_engine_flow(states, ideal=False, show=True, persist=True):
    sequence = states.states if hasattr(states, "states") else states
    stages = sequence[1:]
    fig = go.Figure()

    x_cursor = 0.0
    block_width = 1.55
    annotations = []

    freestream = _state_fields(sequence[0], ideal=ideal)
    annotations.append(
        {
            "x": -0.45,
            "y": 0.0,
            "xref": "x",
            "yref": "y",
            "showarrow": False,
            "align": "right",
            "font": {"size": 10, "color": "#102A43"},
            "text": (
                "<b>Freestream</b><br>"
                f"T = {freestream['T']:.0f} K<br>"
                f"P = {freestream['P'] / 1000.0:.0f} kPa<br>"
                f"V = {freestream['V']:.0f} m/s<br>"
                f"M = {freestream['M']:.2f}"
            ),
        }
    )

    for index, state in enumerate(stages, start=1):
        stage_name = state.stage_name or f"Stage {index}"
        color = BLOCK_COLORS.get(stage_name, "#7B8794")
        text_color = BLOCK_TEXT_COLORS.get(stage_name, "#FFFFFF")
        x0 = x_cursor
        x1 = x_cursor + block_width

        fig.add_shape(
            type="rect",
            x0=x0,
            x1=x1,
            y0=-0.62,
            y1=0.62,
            line={"color": "#102A43", "width": 2},
            fillcolor=color,
            opacity=0.9,
        )
        fig.add_trace(
            go.Scatter(
                x=[x0, x1, x1, x0, x0],
                y=[-0.62, -0.62, 0.62, 0.62, -0.62],
                mode="lines",
                fill="toself",
                fillcolor=color,
                line={"color": "#102A43", "width": 2},
                hovertemplate=(
                    f"<b>{index}. {stage_name}</b><br>"
                    f"T = {getattr(state, 'T_ideal' if ideal else 'T'):.1f} K<br>"
                    f"P = {getattr(state, 'P_ideal' if ideal else 'P') / 1000.0:.1f} kPa<br>"
                    f"Tt = {getattr(state, 'Tt_ideal' if ideal else 'Tt'):.1f} K<br>"
                    f"Pt = {getattr(state, 'Pt_ideal' if ideal else 'Pt') / 1000.0:.1f} kPa<br>"
                    f"V = {getattr(state, 'V_ideal' if ideal else 'V'):.1f} m/s<br>"
                    f"M = {getattr(state, 'M_ideal' if ideal else 'M'):.2f}<extra></extra>"
                ),
                showlegend=False,
            )
        )
        if index >= 1:
            annotations.append(
                {
                    "x": x0 - 0.10,
                    "y": 0.0,
                    "ax": x0 - 0.60,
                    "ay": 0.0,
                    "xref": "x",
                    "yref": "y",
                    "axref": "x",
                    "ayref": "y",
                    "showarrow": True,
                    "arrowhead": 3,
                    "arrowwidth": 1.6,
                    "arrowcolor": "#102A43",
                    "text": "",
                }
            )

        payload = _state_fields(state, ideal=ideal)
        annotations.append(
            {
                "x": 0.5 * (x0 + x1),
                "y": 0.04,
                "xref": "x",
                "yref": "y",
                "showarrow": False,
                "align": "center",
                "font": {"size": 9, "color": text_color},
                "text": (
                    f"<b>{index}. {stage_name}</b><br>"
                    f"T = {payload['T']:.0f} K, P = {payload['P'] / 1000.0:.0f} kPa<br>"
                    f"Tt = {payload['Tt']:.0f} K, Pt = {payload['Pt'] / 1000.0:.0f} kPa<br>"
                    f"V = {payload['V']:.0f} m/s, M = {payload['M']:.2f}<br>"
                    f"A = {payload['A']:.4f} m^2"
                ),
            }
        )
        annotations.append(
            {
                "x": 0.5 * (x0 + x1),
                "y": -0.82,
                "xref": "x",
                "yref": "y",
                "showarrow": False,
                "align": "center",
                "font": {"size": 10, "color": "#486581"},
                "text": PROCESS_NOTES.get(stage_name, ""),
            }
        )
        x_cursor = x1 + 0.55

    fig.add_trace(
        go.Scatter(
            x=[-0.6, x_cursor - 0.15],
            y=[0.0, 0.0],
            mode="lines",
            line={"color": "rgba(16,42,67,0.35)", "width": 1.2},
            hoverinfo="skip",
            showlegend=False,
        )
    )

    final_state = _state_fields(stages[-1], ideal=ideal)
    annotations.append(
        {
            "x": x_cursor - 0.15,
            "y": 0.0,
            "xref": "x",
            "yref": "y",
            "showarrow": False,
            "align": "left",
            "font": {"size": 10, "color": "#102A43"},
            "text": (
                "<b>Exhaust</b><br>"
                f"V = {final_state['V']:.0f} m/s<br>"
                f"M = {final_state['M']:.2f}<br>"
                f"A = {final_state['A']:.4f} m^2"
            ),
        }
    )
    annotations.append(
        {
            "x": 0.5,
            "y": 1.08,
            "xref": "paper",
            "yref": "paper",
            "showarrow": False,
            "align": "left",
            "font": {"size": 11, "color": "#486581"},
            "text": "Station labels show static and total properties at the outlet of each component.",
        }
    )

    fig.update_layout(
        template="plotly_white",
        title={"text": f"{'Theoretical' if ideal else 'Actual'} Brayton Cycle Schematic", "x": 0.04},
        paper_bgcolor="#F6F8FB",
        plot_bgcolor="#EEF3F8",
        font={"family": "Arial", "size": 13, "color": "#102A43"},
        margin={"l": 50, "r": 50, "t": 82, "b": 56},
        annotations=annotations,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, range=[-0.9, max(x_cursor + 0.6, 1.0)])
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, range=[-1.0, 0.95], scaleanchor="x", scaleratio=1)

    if persist:
        OUTPUT_DIR.mkdir(exist_ok=True)
        filename = "engine_flow_ideal.html" if ideal else "engine_flow_actual.html"
        output_path = OUTPUT_DIR / filename
        fig.write_html(output_path, include_plotlyjs=True, full_html=True, auto_open=show)
        print(f"Saved plot: {output_path.resolve()}")
    elif show:
        fig.show()
    return fig
