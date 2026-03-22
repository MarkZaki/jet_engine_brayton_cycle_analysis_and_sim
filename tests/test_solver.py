import unittest
import math

from configs.default import get_default_config
from models.atmosphere import isa_atmosphere
from models.gas import STANDARD_AIR, build_gas_from_config
from performance.efficiency import jet_power_efficiency, overall_efficiency, propulsive_efficiency
from performance.metrics import summarize_result
from solver.base import FlowState
from solver.engine import run_engine_case, sweep_flight_envelope
from solver.stages.combustor import Combustor
from solver.stages.compressor import Compressor
from solver.stages.inlet import Inlet
from solver.stages.nozzle import Nozzle
from solver.stages.turbine import Turbine


class SolverPhysicsTests(unittest.TestCase):
    def test_gas_model_produces_consistent_gas_constant(self):
        gas = build_gas_from_config(get_default_config())
        expected_r = gas.cp * (gas.gamma - 1.0) / gas.gamma
        self.assertAlmostEqual(gas.R, expected_r, places=6)

    def test_inlet_preserves_total_temperature_and_loses_total_pressure(self):
        gas = STANDARD_AIR
        state = FlowState(T=288.15, P=101325.0, V=210.0, m_dot=5.0, gas=gas)
        stage = Inlet(pressure_recovery=0.97, exit_velocity=85.0, gas=gas)

        out = stage.process(state)

        self.assertAlmostEqual(out.Tt, state.Tt, places=6)
        self.assertLess(out.Pt, state.Pt)
        self.assertAlmostEqual(out.Tt_ideal, state.Tt_ideal, places=6)
        self.assertAlmostEqual(out.Pt_ideal, state.Pt_ideal, places=6)

    def test_compressor_actual_temperature_exceeds_ideal_reference(self):
        gas = STANDARD_AIR
        state = FlowState(T=300.0, P=101325.0, V=90.0, m_dot=5.0, gas=gas)
        stage = Compressor(pressure_ratio=8.0, eta_c=0.84, exit_velocity=120.0, gas=gas)

        out = stage.process(state)

        self.assertGreater(out.Tt, state.Tt)
        self.assertAlmostEqual(out.Pt / state.Pt, 8.0, places=6)
        self.assertGreater(out.Tt, out.Tt_ideal)
        self.assertGreater(out.Wc, out.Wc_ideal)

    def test_combustor_generates_positive_fuel_air_ratio_and_target_turbine_inlet_temperature(self):
        gas = STANDARD_AIR
        state = FlowState(T=650.0, P=900000.0, V=110.0, m_dot=5.0, gas=gas)
        stage = Combustor(T3=1450.0, pressure_loss=0.04, exit_velocity=70.0, gas=gas)

        out = stage.process(state)

        self.assertGreater(out.fuel_air_ratio, 0.0)
        self.assertGreater(out.Qin, 0.0)
        self.assertAlmostEqual(out.Tt, 1450.0, places=6)
        self.assertAlmostEqual(out.Pt / state.Pt, 0.96, places=6)

    def test_turbine_matches_required_shaft_work(self):
        gas = STANDARD_AIR
        state = FlowState(T=1100.0, P=500000.0, V=70.0, m_dot=8.0, gas=gas)
        state.Wc = 220000.0
        state.Wc_ideal = 200000.0
        state.fuel_air_ratio = 0.02
        state.fuel_air_ratio_ideal = 0.02
        state.update_derived()
        stage = Turbine(eta_t=0.90, eta_mech=0.95, exit_velocity=150.0, gas=gas)

        out = stage.process(state)

        self.assertAlmostEqual(out.Wt - state.Wt, state.Wc / 0.95, places=6)
        self.assertAlmostEqual(out.Wt_ideal - state.Wt_ideal, state.Wc_ideal, places=6)
        self.assertLess(out.Pt, state.Pt)

    def test_nozzle_detects_choked_flow_and_satisfies_continuity(self):
        gas = STANDARD_AIR
        state = FlowState(T=1100.0, P=500000.0, V=150.0, m_dot=8.0, gas=gas)
        state.fuel_air_ratio = 0.02
        state.update_derived()
        stage = Nozzle(gas=gas, Pe=101325.0, eta_n=0.97)

        out = stage.process(state)

        self.assertTrue(out.nozzle_choked)
        self.assertGreater(out.pressure_thrust, 0.0)
        self.assertGreater(out.V, 0.0)
        self.assertGreater(out.exit_area, 0.0)
        self.assertAlmostEqual(out.m_dot_actual, out.rho * out.V * out.exit_area, places=5)

    def test_engine_run_returns_station_and_component_tables(self):
        result = run_engine_case({**get_default_config(), "verbose": False})
        station_frame = result.to_dataframe()
        component_frame = result.to_component_dataframe()

        self.assertEqual(len(result.states), len(station_frame))
        self.assertIn("actual_total_temperature_K", station_frame.columns)
        self.assertIn("ideal_total_pressure_kPa", station_frame.columns)
        self.assertIn("fuel_air_ratio", station_frame.columns)
        self.assertIn("infeasible", station_frame.columns)
        self.assertIn("status_message", station_frame.columns)
        self.assertGreater(len(component_frame), 0)
        self.assertIn("actual_total_pressure_ratio", component_frame.columns)

    def test_flight_envelope_sweep_returns_full_grid(self):
        config = {**get_default_config(), "verbose": False}
        sweep = sweep_flight_envelope(config, [0.0, 5000.0, 10000.0], [100.0, 200.0, 300.0])

        self.assertEqual(len(sweep), 9)
        self.assertIn("thrust_N", sweep.columns)
        self.assertIn("overall_efficiency", sweep.columns)

    def test_direct_engine_run_uses_isa_ambient_conditions_for_altitude(self):
        altitude_m = 5000.0
        atmosphere = isa_atmosphere(altitude_m)

        result = run_engine_case({"altitude_m": altitude_m, "verbose": False})

        self.assertAlmostEqual(result.states[0].T, atmosphere.temperature, places=6)
        self.assertAlmostEqual(result.states[0].P, atmosphere.pressure, places=6)

    def test_propulsive_efficiency_is_distinct_from_overall_efficiency(self):
        config = {**get_default_config(), "verbose": False}
        result = run_engine_case(config)
        state = result.final_state
        V0 = config["flight_speed"]

        eta_propulsive = propulsive_efficiency(state, V0)
        eta_overall = overall_efficiency(state, V0)
        eta_jet = jet_power_efficiency(state, V0)

        self.assertAlmostEqual(eta_propulsive * eta_jet, eta_overall, places=6)
        self.assertNotAlmostEqual(eta_propulsive, eta_overall, places=6)

    def test_invalid_configs_are_rejected_before_solver_execution(self):
        with self.assertRaises(ValueError):
            run_engine_case({"compressor_efficiency": 0.0, "verbose": False})

        with self.assertRaises(ValueError):
            run_engine_case({"mass_flow_rate": -1.0, "verbose": False})

    def test_infeasible_cycle_is_flagged_instead_of_returning_impossible_area(self):
        result = run_engine_case({"turbine_inlet_temperature": 500.0, "verbose": False})
        summary = summarize_result(result, V0=200.0)

        self.assertTrue(result.final_state.infeasible)
        self.assertFalse(summary["feasible"])
        self.assertTrue(math.isnan(result.final_state.exit_area))
        self.assertGreater(len(summary["warnings"]), 0)

    def test_afterburner_stage_adds_fuel_and_boosts_thrust(self):
        base_config = {**get_default_config(), "verbose": False}
        dry_result = run_engine_case(base_config)
        wet_result = run_engine_case(
            {
                **base_config,
                "afterburner_enabled": True,
                "afterburner_exit_temperature": 1900.0,
            }
        )

        dry_summary = summarize_result(dry_result, V0=base_config["flight_speed"])
        wet_summary = summarize_result(wet_result, V0=base_config["flight_speed"])
        wet_stage_names = [state.stage_name for state in wet_result.states]

        self.assertIn("Afterburner", wet_stage_names)
        self.assertGreater(wet_result.final_state.fuel_air_ratio, dry_result.final_state.fuel_air_ratio)
        self.assertGreater(wet_summary["thrust_N"], dry_summary["thrust_N"])


if __name__ == "__main__":
    unittest.main()
