from configs.default import get_default_config
from performance.metrics import summarize_result
from solver.engine import run_engine_case
from visualization.plots import plot_PV, plot_TP, plot_TS, plot_engine_flow, plot_performance


def main():
    config = get_default_config()
    result = run_engine_case(config)
    summary = summarize_result(result, V0=config["flight_speed"])

    print("---- ENGINE RESULTS ----")
    print(f"Thrust: {summary['thrust_N']:.2f} N")
    print(f"Specific thrust: {summary['specific_thrust_N_per_kg_s']:.2f} N/(kg/s)")
    print(f"Fuel-air ratio: {summary['fuel_air_ratio']:.5f}")
    print(f"Overall efficiency: {summary['overall_efficiency']:.4f}")
    print(f"Jet power efficiency: {summary['jet_power_efficiency']:.4f}")
    print(f"BWR: {summary['bwr']:.4f}")
    print(f"Nozzle choked: {summary['nozzle_choked']}")

    plot_PV(result, show=False, persist=True)
    plot_TS(result, show=False, persist=True)
    plot_TP(result, show=False, persist=True)
    plot_performance(result, show=False, persist=True)
    plot_engine_flow(result, show=False, persist=True)


if __name__ == "__main__":
    main()
