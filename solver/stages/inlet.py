from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import (
    entropy_change,
    stagnation_pressure_from_static,
    static_pressure_from_stagnation,
    static_temperature_from_total,
    total_temperature,
)


class Inlet(Stage):
    def __init__(
        self,
        pressure_recovery=0.98,
        exit_velocity=0.0,
        gas=STANDARD_AIR,
    ):
        super().__init__("Inlet")
        self.pressure_recovery = pressure_recovery
        self.exit_velocity = exit_velocity
        self.gas = gas

    def _diffuse(self, temperature, pressure, velocity, recovery):
        T_total = total_temperature(temperature, velocity, self.gas.cp)
        P_total = stagnation_pressure_from_static(temperature, pressure, T_total, self.gas.gamma)
        T_exit = static_temperature_from_total(T_total, self.exit_velocity, self.gas.cp)
        P_exit_total = recovery * P_total
        P_exit = static_pressure_from_stagnation(T_exit, T_total, P_exit_total, self.gas.gamma)
        return T_exit, P_exit

    def process(self, state: FlowState) -> FlowState:
        T2, P2 = self._diffuse(state.T, state.P, state.V, self.pressure_recovery)
        T2_ideal, P2_ideal = self._diffuse(
            state.T_ideal,
            state.P_ideal,
            state.V_ideal,
            recovery=1.0,
        )

        new_state = state.copy()
        new_state.T = T2
        new_state.P = P2
        new_state.V = self.exit_velocity
        new_state.s += entropy_change(T2, state.T, P2, state.P, self.gas.cp, state.R)

        new_state.T_ideal = T2_ideal
        new_state.P_ideal = P2_ideal
        new_state.V_ideal = self.exit_velocity
        new_state.s_ideal = state.s_ideal

        new_state.update_derived()
        return new_state
