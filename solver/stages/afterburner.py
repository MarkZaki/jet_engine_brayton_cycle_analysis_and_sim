from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, fuel_air_ratio_for_target_temperature


class Afterburner(Stage):
    def __init__(
        self,
        Tt_out,
        pressure_loss=0.04,
        exit_velocity=170.0,
        gas=STANDARD_AIR,
        burner_efficiency=None,
    ):
        super().__init__("Afterburner")
        self.Tt_out = Tt_out
        self.pressure_loss = pressure_loss
        self.exit_velocity = exit_velocity
        self.gas = gas
        self.burner_efficiency = burner_efficiency if burner_efficiency is not None else gas.burner_efficiency

    def process(self, state: FlowState) -> FlowState:
        Pt_out = state.Pt * (1.0 - self.pressure_loss)
        Pt_out_ideal = state.Pt_ideal
        target_temperature = max(self.Tt_out, state.Tt)
        target_temperature_ideal = max(self.Tt_out, state.Tt_ideal)

        fuel_air_ratio = fuel_air_ratio_for_target_temperature(
            target_temperature,
            state.Tt,
            self.gas,
            self.burner_efficiency,
        )
        fuel_air_ratio_ideal = fuel_air_ratio_for_target_temperature(
            target_temperature_ideal,
            state.Tt_ideal,
            self.gas,
            burner_efficiency=1.0,
        )

        new_state = state.copy()
        new_state.set_actual_total(target_temperature, Pt_out, self.exit_velocity)
        new_state.s += entropy_change(target_temperature, state.Tt, Pt_out, state.Pt, self.gas)
        new_state.Qin += fuel_air_ratio * self.gas.lower_heating_value
        new_state.fuel_air_ratio += fuel_air_ratio
        if self.Tt_out <= state.Tt:
            new_state.add_warning("Afterburner target temperature was below the turbine exit total temperature; no extra fuel was added.")

        new_state.set_ideal_total(target_temperature_ideal, Pt_out_ideal, self.exit_velocity)
        new_state.s_ideal += entropy_change(
            target_temperature_ideal,
            state.Tt_ideal,
            Pt_out_ideal,
            state.Pt_ideal,
            self.gas,
        )
        new_state.Qin_ideal += fuel_air_ratio_ideal * self.gas.lower_heating_value
        new_state.fuel_air_ratio_ideal += fuel_air_ratio_ideal

        new_state.update_derived()
        return new_state
