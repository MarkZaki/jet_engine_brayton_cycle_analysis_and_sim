import unittest

from configs.default import get_default_config
from models.gas import STANDARD_AIR, build_gas_from_config
from solver.base import FlowState
from solver.engine import run_engine_case
from solver.stages.combustor import Combustor
from solver.stages.compressor import Compressor
from solver.stages.nozzle import Nozzle


class SolverPhysicsTests(unittest.TestCase):
    def test_gas_model_produces_consistent_gas_constant(self):
        gas = build_gas_from_config(get_default_config())
        expected_r = gas.cp * (gas.gamma - 1.0) / gas.gamma
        self.assertAlmostEqual(gas.R, expected_r, places=6)

    def test_compressor_actual_temperature_exceeds_ideal_reference(self):
        gas = STANDARD_AIR
        state = FlowState(T=300.0, P=101325.0, V=0.0, m_dot=5.0, gas=gas)
        stage = Compressor(pressure_ratio=8.0, eta_c=0.84, gas=gas)

        out = stage.process(state)

        self.assertGreater(out.T, out.T_ideal)
        self.assertGreater(out.Wc, out.Wc_ideal)

    def test_combustor_generates_positive_fuel_air_ratio(self):
        gas = STANDARD_AIR
        state = FlowState(T=650.0, P=900000.0, V=0.0, m_dot=5.0, gas=gas)
        stage = Combustor(T3=1450.0, pressure_loss=0.04, gas=gas)

        out = stage.process(state)

        self.assertGreater(out.fuel_air_ratio, 0.0)
        self.assertGreater(out.Qin, 0.0)
        self.assertLess(out.P, state.P)

    def test_nozzle_detects_choked_flow(self):
        gas = STANDARD_AIR
        state = FlowState(T=1100.0, P=500000.0, V=0.0, m_dot=8.0, gas=gas)
        state.fuel_air_ratio = 0.02
        stage = Nozzle(gas=gas, Pe=101325.0, eta_n=0.97)

        out = stage.process(state)

        self.assertTrue(out.nozzle_choked)
        self.assertGreater(out.pressure_thrust, 0.0)
        self.assertGreater(out.V, 0.0)

    def test_engine_run_returns_station_dataframe(self):
        result = run_engine_case({**get_default_config(), "verbose": False})
        frame = result.to_dataframe()

        self.assertEqual(len(result.states), len(frame))
        self.assertIn("actual_temperature_K", frame.columns)
        self.assertIn("fuel_air_ratio", frame.columns)


if __name__ == "__main__":
    unittest.main()
