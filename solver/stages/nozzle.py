from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import nozzle_exit_state


class Nozzle(Stage):
    def __init__(self, gas=STANDARD_AIR, Pe=101325.0, eta_n=0.97):
        super().__init__("Nozzle")
        self.gas = gas
        self.Pe = Pe
        self.eta_n = eta_n

    def process(self, state: FlowState) -> FlowState:
        exit_actual = nozzle_exit_state(
            state.T,
            state.P,
            self.Pe,
            self.gas,
            self.eta_n,
            state.m_dot * (1.0 + state.fuel_air_ratio),
        )
        exit_ideal = nozzle_exit_state(
            state.T_ideal,
            state.P_ideal,
            self.Pe,
            self.gas,
            1.0,
            state.m_dot * (1.0 + state.fuel_air_ratio_ideal),
        )

        new_state = state.copy()
        new_state.T = exit_actual["temperature"]
        new_state.P = exit_actual["pressure"]
        new_state.V = exit_actual["velocity"]
        new_state.pressure_thrust = exit_actual["pressure_thrust"]
        new_state.exit_area = exit_actual["exit_area"]
        new_state.nozzle_choked = exit_actual["choked"]

        new_state.T_ideal = exit_ideal["temperature"]
        new_state.P_ideal = exit_ideal["pressure"]
        new_state.V_ideal = exit_ideal["velocity"]
        new_state.pressure_thrust_ideal = exit_ideal["pressure_thrust"]
        new_state.exit_area_ideal = exit_ideal["exit_area"]
        new_state.nozzle_choked_ideal = exit_ideal["choked"]

        new_state.update_derived()
        return new_state
