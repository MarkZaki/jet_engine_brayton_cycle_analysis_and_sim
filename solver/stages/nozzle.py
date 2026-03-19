from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, nozzle_exit_state


class Nozzle(Stage):
    def __init__(self, gas=STANDARD_AIR, Pe=101325.0, eta_n=0.97):
        super().__init__("Nozzle")
        self.gas = gas
        self.Pe = Pe
        self.eta_n = eta_n

    def process(self, state: FlowState) -> FlowState:
        exit_actual = nozzle_exit_state(
            state.Tt,
            state.Pt,
            self.Pe,
            self.gas,
            self.eta_n,
            state.m_dot_actual,
        )
        exit_ideal = nozzle_exit_state(
            state.Tt_ideal,
            state.Pt_ideal,
            self.Pe,
            self.gas,
            1.0,
            state.m_dot_ideal,
        )

        new_state = state.copy()
        new_state.set_actual_static(
            exit_actual["temperature"],
            exit_actual["pressure"],
            exit_actual["velocity"],
        )
        new_state.s += entropy_change(new_state.T, state.T, new_state.P, state.P, self.gas.cp, state.R)
        new_state.pressure_thrust = exit_actual["pressure_thrust"]
        new_state.exit_area = exit_actual["exit_area"]
        new_state.throat_area = exit_actual["throat_area"]
        new_state.nozzle_choked = exit_actual["choked"]

        new_state.set_ideal_static(
            exit_ideal["temperature"],
            exit_ideal["pressure"],
            exit_ideal["velocity"],
        )
        new_state.s_ideal += entropy_change(
            new_state.T_ideal,
            state.T_ideal,
            new_state.P_ideal,
            state.P_ideal,
            self.gas.cp,
            state.R,
        )
        new_state.pressure_thrust_ideal = exit_ideal["pressure_thrust"]
        new_state.exit_area_ideal = exit_ideal["exit_area"]
        new_state.throat_area_ideal = exit_ideal["throat_area"]
        new_state.nozzle_choked_ideal = exit_ideal["choked"]

        new_state.update_derived()
        return new_state
