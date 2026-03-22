from __future__ import annotations

from models.gas import STANDARD_AIR
from solver.base import FlowState, Stage
from solver.cycle import entropy_change, nozzle_exit_state


class Nozzle(Stage):
    def __init__(
        self,
        gas=STANDARD_AIR,
        Pe: float = 101325.0,
        eta_n: float = 0.97,
        nozzle_type: str = "convergent",
        throat_area: float | None = None,
        exit_area: float | None = None,
        pressure_loss: float = 0.0,
        name: str = "Nozzle",
    ) -> None:
        super().__init__(name)
        self.gas = gas
        self.Pe = Pe
        self.eta_n = eta_n
        self.nozzle_type = nozzle_type
        self.throat_area = throat_area
        self.exit_area = exit_area
        self.pressure_loss = pressure_loss

    def process(self, state: FlowState) -> FlowState:
        exit_actual = nozzle_exit_state(
            state.Tt,
            state.Pt,
            self.Pe,
            self.gas,
            self.eta_n,
            state.m_dot_actual,
            nozzle_type=self.nozzle_type,
            throat_area=self.throat_area,
            exit_area=self.exit_area,
            total_pressure_loss=self.pressure_loss,
        )
        exit_ideal = nozzle_exit_state(
            state.Tt_ideal,
            state.Pt_ideal,
            self.Pe,
            self.gas,
            1.0,
            state.m_dot_ideal,
            nozzle_type=self.nozzle_type,
            throat_area=self.throat_area,
            exit_area=self.exit_area,
            total_pressure_loss=0.0,
        )

        new_state = state.copy()
        new_state.set_actual_static(
            float(exit_actual["temperature"]),
            float(exit_actual["pressure"]),
            float(exit_actual["velocity"]),
        )
        new_state.s += entropy_change(new_state.T, state.T, new_state.P, state.P, self.gas)
        new_state.pressure_thrust = float(exit_actual["pressure_thrust"])
        new_state.exit_area = float(exit_actual["exit_area"])
        new_state.throat_area = float(exit_actual["throat_area"])
        new_state.nozzle_choked = bool(exit_actual["choked"])
        if abs(float(exit_actual["continuity_error"])) > 0.03:
            new_state.add_warning(f"{self.name} continuity mismatch is {float(exit_actual['continuity_error']):.1%}.")
        if not bool(exit_actual["feasible"]):
            new_state.mark_infeasible(str(exit_actual["message"]))

        new_state.set_ideal_static(
            float(exit_ideal["temperature"]),
            float(exit_ideal["pressure"]),
            float(exit_ideal["velocity"]),
        )
        new_state.s_ideal += entropy_change(
            new_state.T_ideal,
            state.T_ideal,
            new_state.P_ideal,
            state.P_ideal,
            self.gas,
        )
        new_state.pressure_thrust_ideal = float(exit_ideal["pressure_thrust"])
        new_state.exit_area_ideal = float(exit_ideal["exit_area"])
        new_state.throat_area_ideal = float(exit_ideal["throat_area"])
        new_state.nozzle_choked_ideal = bool(exit_ideal["choked"])
        if not bool(exit_ideal["feasible"]):
            new_state.add_warning(f"Ideal {self.name.lower()} branch: {exit_ideal['message']}")

        new_state.update_derived()
        return new_state
