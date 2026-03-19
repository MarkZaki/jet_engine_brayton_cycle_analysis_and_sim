from models.atmosphere import Cp, gamma
from performance.metrics import compute_bwr
from solver.base import FlowState
from solver.engine import Engine
from solver.stages.compressor import Compressor
from solver.stages.combustor import Combustor
from solver.stages.turbine import Turbine

from solver.stages.nozzle import Nozzle
from performance.thrust import compute_thrust
from performance.efficiency import power_efficiency, shaft_efficiency
from visualization.plots import plot_PV,plot_TP,plot_TS,plot_performance

engine = Engine([
    Compressor(pressure_ratio=10, eta_c=0.85),
    Combustor(T3=1500, pressure_loss=0.05),
    Turbine(eta_t=0.9, eta_mech=0.95),
    Nozzle(cp=1005, Pe=101325, gamma=1.4)
])

state0 = FlowState(T=288, P=101325, m_dot=10, V=0, Wc=0, Wt=0, Qin=0)

states = engine.run(state0)
final = states[-1]

bwr = compute_bwr(final)
thrust = compute_thrust(final, V0=200)
eta_mech = shaft_efficiency(final)
eta_power = power_efficiency(final, V0=200)
eta = eta_mech * eta_power

print("---- ENGINE RESULTS ----")
print("Thrust:", thrust)
print("Efficiency:", eta_power)
print("BWR:", bwr)

plot_PV(states)
plot_TS(states)
plot_TP(states)
plot_performance(states)