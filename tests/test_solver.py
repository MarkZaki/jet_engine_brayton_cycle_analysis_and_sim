import unittest

from configs.default import get_default_config
from models.atmosphere import isa_atmosphere
from models.gas import build_gas_from_config
from performance.efficiency import overall_efficiency, propulsive_efficiency, thermal_efficiency
from performance.metrics import summarize_result
from solver.engine import prepare_config, run_engine_case, sweep_parameter


class SolverTests(unittest.TestCase):
    def test_gas_model_produces_consistent_gas_constant(self):
        gas = build_gas_from_config(get_default_config())
        expected_r = gas.cp * (gas.gamma - 1.0) / gas.gamma
        self.assertAlmostEqual(gas.R, expected_r, places=6)

    def test_prepare_config_resolves_mach_to_speed(self):
        config = prepare_config({"flight_input_mode": "mach", "flight_mach_number": 0.5, "verbose": False})
        self.assertGreater(config.flight_speed, 0.0)

    def test_direct_engine_run_uses_isa_ambient_conditions_for_altitude(self):
        altitude_m = 5000.0
        atmosphere = isa_atmosphere(altitude_m)
        result = run_engine_case({"altitude_m": altitude_m, "verbose": False})

        self.assertAlmostEqual(result.states[0].T, atmosphere.temperature, places=6)
        self.assertAlmostEqual(result.states[0].P, atmosphere.pressure, places=6)

    def test_engine_run_has_course_stage_sequence(self):
        result = run_engine_case({**get_default_config(), "verbose": False})
        stage_names = [state.stage_name for state in result.states]

        self.assertEqual(stage_names, ["Freestream", "Inlet", "Compressor", "Combustor", "Turbine", "Nozzle"])

    def test_combustor_adds_heat_and_fuel(self):
        result = run_engine_case({**get_default_config(), "verbose": False})
        combustor_state = result.states[3]

        self.assertGreater(combustor_state.Qin, 0.0)
        self.assertGreater(combustor_state.fuel_air_ratio, 0.0)
        self.assertAlmostEqual(combustor_state.Tt, result.config["turbine_inlet_temperature"], places=6)

    def test_turbine_supplies_positive_work_and_nozzle_accelerates_flow(self):
        result = run_engine_case({**get_default_config(), "verbose": False})
        turbine_state = result.states[4]
        nozzle_state = result.states[5]

        self.assertGreater(turbine_state.Wt, 0.0)
        self.assertGreater(nozzle_state.V, turbine_state.V)
        self.assertGreater(nozzle_state.exit_area, 0.0)

    def test_efficiency_relation_holds(self):
        result = run_engine_case({**get_default_config(), "verbose": False})
        state = result.final_state
        V0 = result.config["flight_speed"]

        eta_overall = overall_efficiency(state, V0)
        eta_thermal = thermal_efficiency(state, V0)
        eta_propulsive = propulsive_efficiency(state, V0)

        self.assertAlmostEqual(eta_thermal * eta_propulsive, eta_overall, places=6)

    def test_engine_run_returns_station_and_component_tables(self):
        result = run_engine_case({**get_default_config(), "verbose": False})
        station_frame = result.to_dataframe()
        component_frame = result.to_component_dataframe()

        self.assertEqual(len(result.states), len(station_frame))
        self.assertIn("actual_total_temperature_K", station_frame.columns)
        self.assertIn("ideal_total_pressure_kPa", station_frame.columns)
        self.assertIn("status_message", station_frame.columns)
        self.assertGreater(len(component_frame), 0)
        self.assertIn("actual_total_pressure_ratio", component_frame.columns)

    def test_parameter_sweep_returns_requested_points(self):
        sweep = sweep_parameter(get_default_config(), "compressor_pressure_ratio", [4.0, 8.0, 12.0])

        self.assertEqual(len(sweep), 3)
        self.assertIn("thrust_N", sweep.columns)
        self.assertIn("overall_efficiency", sweep.columns)

    def test_flight_speed_sweep_uses_direct_speed_values(self):
        sweep = sweep_parameter(
            {
                **get_default_config(),
                "flight_input_mode": "mach",
                "flight_mach_number": 0.6,
                "verbose": False,
            },
            "flight_speed",
            [100.0, 300.0],
        )

        self.assertEqual(sweep["flight_speed"].tolist(), [100.0, 300.0])
        self.assertNotEqual(float(sweep.iloc[0]["thrust_N"]), float(sweep.iloc[1]["thrust_N"]))

    def test_invalid_configs_are_rejected(self):
        with self.assertRaises(ValueError):
            run_engine_case({"compressor_efficiency": 0.0, "verbose": False})

        with self.assertRaises(ValueError):
            run_engine_case({"mass_flow_rate": -1.0, "verbose": False})

    def test_summary_reports_positive_main_metrics(self):
        result = run_engine_case({**get_default_config(), "verbose": False})
        summary = summarize_result(result, V0=result.config["flight_speed"])

        self.assertGreater(summary["thrust_N"], 0.0)
        self.assertGreater(summary["specific_thrust_N_per_kg_s"], 0.0)
        self.assertGreater(summary["fuel_flow_kg_s"], 0.0)


if __name__ == "__main__":
    unittest.main()
