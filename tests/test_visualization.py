import unittest

from configs.default import get_default_config
from solver.engine import run_engine_case, sweep_flight_envelope
from visualization.plots import (
    figure_to_html_bytes,
    plot_PV,
    plot_TS,
    plot_TP,
    plot_engine_flow,
    plot_operating_map,
    plot_performance,
)


class VisualizationTests(unittest.TestCase):
    def setUp(self):
        self.result = run_engine_case({**get_default_config(), "verbose": False})
        self.afterburner_result = run_engine_case(
            {
                **get_default_config(),
                "afterburner_enabled": True,
                "afterburner_exit_temperature": 1900.0,
                "verbose": False,
            }
        )

    def test_cycle_figures_build_without_persisting(self):
        figures = [
            plot_PV(self.result, show=False, persist=False),
            plot_TS(self.result, show=False, persist=False),
            plot_TP(self.result, show=False, persist=False),
            plot_performance(self.result, show=False, persist=False),
            plot_engine_flow(self.result, show=False, persist=False),
            plot_engine_flow(self.result, ideal=True, show=False, persist=False),
        ]

        for fig in figures:
            payload = fig.to_plotly_json()
            self.assertGreater(len(payload["data"]), 0)

    def test_operating_map_builds_and_exports_html(self):
        envelope = sweep_flight_envelope(get_default_config(), [0.0, 4000.0, 8000.0], [100.0, 200.0, 300.0])
        figure = plot_operating_map(envelope, metric="thrust_N", show=False, persist=False)
        html_bytes = figure_to_html_bytes(figure)

        self.assertGreater(len(figure.to_plotly_json()["data"]), 0)
        self.assertIn(b"plotly", html_bytes.lower())

    def test_performance_plot_uses_stage_deltas_and_afterburner_renders(self):
        performance_figure = plot_performance(self.result, show=False, persist=False)
        wet_figures = [
            plot_TS(self.afterburner_result, show=False, persist=False),
            plot_engine_flow(self.afterburner_result, show=False, persist=False),
        ]

        performance_payload = performance_figure.to_plotly_json()
        self.assertEqual(len(performance_payload["data"][0]["x"]), len(self.result.states) - 1)
        for fig in wet_figures:
            self.assertGreater(len(fig.to_plotly_json()["data"]), 0)


if __name__ == "__main__":
    unittest.main()
