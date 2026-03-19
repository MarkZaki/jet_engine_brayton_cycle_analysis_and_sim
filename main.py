from models.atmosphere import Cp, gamma
from performance.efficiency import power_efficiency, shaft_efficiency
from performance.metrics import compute_bwr
from performance.thrust import compute_thrust
from solver.base import FlowState
from solver.engine import Engine
from solver.stages.combustor import Combustor
from solver.stages.compressor import Compressor
from solver.stages.nozzle import Nozzle
from solver.stages.turbine import Turbine
from visualization.plots import plot_PV, plot_TP, plot_TS, plot_performance


def main():
    flight_speed = 200.0

    engine = Engine(
        [
            Compressor(pressure_ratio=10.0, eta_c=0.85),
            Combustor(T3=1500.0, pressure_loss=0.05),
            Turbine(eta_t=0.90, eta_mech=0.95),
            Nozzle(cp=Cp, Pe=101325.0, gamma=gamma),
        ]
    )

    state0 = FlowState(
        T=288.0,
        P=101325.0,
        V=flight_speed,
        m_dot=10.0,
    )
    state0.stage_name = "Freestream"

    states = engine.run(state0)
    final_state = states[-1]

    print("---- ENGINE RESULTS ----")
    print(f"Exit velocity (actual): {final_state.V:.2f} m/s")
    print(f"Exit velocity (ideal): {final_state.V_ideal:.2f} m/s")
    print(f"Thrust: {compute_thrust(final_state, V0=flight_speed):.2f} N")
    print(f"Thermal efficiency proxy: {shaft_efficiency(final_state):.4f}")
    print(f"Jet power efficiency: {power_efficiency(final_state, V0=flight_speed):.4f}")
    print(f"BWR: {compute_bwr(final_state):.4f}")

    plot_PV(states)
    plot_TS(states)
    plot_TP(states)
    plot_performance(states)


if __name__ == "__main__":
    main()
