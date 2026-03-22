import unittest

from configs.default import get_default_config
from solver.engine import run_engine_case
from visualization.plots import (
    plot_PV,
    plot_TS,
    plot_TP,
    plot_engine_flow,
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
            self.assertTrue(len(payload["data"]) > 0 or len(payload["layout"].get("shapes", [])) > 0)

    def test_engine_flow_is_simple_block_schematic(self):
        figure = plot_engine_flow(self.result, show=False, persist=False)
        payload = figure.to_plotly_json()

        self.assertGreater(len(payload["layout"]["shapes"]), 0)
        self.assertGreater(len(payload["layout"]["annotations"]), 0)


if __name__ == "__main__":
    unittest.main()
