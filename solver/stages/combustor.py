from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, fuel_air_ratio_for_target_temperature


class Combustor(Stage):
    def __init__(self, T3, pressure_loss=0.05, gas=STANDARD_AIR, burner_efficiency=None):
        super().__init__("Combustor")
        self.T3 = T3
        self.pressure_loss = pressure_loss
        self.gas = gas
        self.burner_efficiency = burner_efficiency if burner_efficiency is not None else gas.burner_efficiency

    def process(self, state: FlowState) -> FlowState:
        P3 = state.P * (1.0 - self.pressure_loss)
        P3_ideal = state.P_ideal
        fuel_air_ratio = fuel_air_ratio_for_target_temperature(
            self.T3,
            state.T,
            self.gas,
            self.burner_efficiency,
        )
        fuel_air_ratio_ideal = fuel_air_ratio_for_target_temperature(
            self.T3,
            state.T_ideal,
            self.gas,
            burner_efficiency=1.0,
        )

        new_state = state.copy()
        new_state.T = self.T3
        new_state.P = P3
        new_state.s += entropy_change(self.T3, state.T, P3, state.P, self.gas.cp, state.R)
        new_state.Qin += fuel_air_ratio * self.gas.lower_heating_value
        new_state.fuel_air_ratio += fuel_air_ratio

        new_state.T_ideal = self.T3
        new_state.P_ideal = P3_ideal
        new_state.s_ideal += entropy_change(
            self.T3,
            state.T_ideal,
            P3_ideal,
            state.P_ideal,
            self.gas.cp,
            state.R,
        )
        new_state.Qin_ideal += fuel_air_ratio_ideal * self.gas.lower_heating_value
        new_state.fuel_air_ratio_ideal += fuel_air_ratio_ideal

        new_state.update_derived()
        return new_state
