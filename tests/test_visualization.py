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


if __name__ == "__main__":
    unittest.main()
