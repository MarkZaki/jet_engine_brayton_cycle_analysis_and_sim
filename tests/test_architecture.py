import unittest

from configs.default import EngineConfig, get_preset_config, list_presets
from models.atmosphere import isa_atmosphere
from performance.metrics import summarize_result
from solver.engine import prepare_config, run_engine_case
from solver.cycle import speed_of_sound


class ArchitectureAndConfigTests(unittest.TestCase):
    def test_prepare_config_returns_typed_engine_config(self):
        config = prepare_config({"preset_name": "Turbojet", "verbose": False})

        self.assertIsInstance(config, EngineConfig)
        self.assertEqual(config.preset_name, "Turbojet")

    def test_turbofan_preset_produces_positive_bypass_thrust(self):
        result = run_engine_case({**get_preset_config("Low-Bypass Turbofan"), "verbose": False})
        summary = summarize_result(result, V0=result.config["flight_speed"])

        self.assertEqual(summary["architecture"], "turbofan")
        self.assertGreater(summary["bypass_thrust_N"], 0.0)
        self.assertGreater(summary["bypass_air_mass_flow_kg_s"], 0.0)

    def test_mach_input_resolves_expected_flight_speed(self):
        altitude_m = 11000.0
        mach_number = 0.82
        atmosphere = isa_atmosphere(altitude_m)
        result = run_engine_case(
            {
                "altitude_m": altitude_m,
                "flight_input_mode": "mach",
                "flight_mach_number": mach_number,
                "verbose": False,
            }
        )
        expected_speed = mach_number * speed_of_sound(atmosphere.temperature, result.gas)

        self.assertAlmostEqual(result.config["flight_speed"], expected_speed, places=6)

    def test_fixed_nozzle_geometry_can_trigger_infeasible_flag(self):
        baseline = run_engine_case({"verbose": False})
        result = run_engine_case(
            {
                "core_nozzle_type": "converging-diverging",
                "core_nozzle_throat_area": baseline.final_state.throat_area * 0.5,
                "core_nozzle_exit_area": baseline.final_state.exit_area * 1.5,
                "verbose": False,
            }
        )

        self.assertTrue(result.final_state.infeasible)
        self.assertGreater(len(result.final_state.warnings), 0)

    def test_presets_are_available(self):
        self.assertIn("Turbojet", list_presets())
        self.assertIn("Low-Bypass Turbofan", list_presets())


if __name__ == "__main__":
    unittest.main()
