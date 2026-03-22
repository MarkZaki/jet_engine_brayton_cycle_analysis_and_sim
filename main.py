from configs.default import get_default_config
from performance.metrics import summarize_result
from performance.reporting import export_result_tables, write_html_report
from solver.engine import run_engine_case, sweep_flight_envelope
from visualization.plots import (
    plot_PV,
    plot_TP,
    plot_TS,
    plot_engine_flow,
    plot_operating_map,
    plot_performance,
)


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
    print(f"Feasible operating point: {summary['feasible']}")
    print(f"Exit Mach: {summary['exit_mach']:.3f}")
    print(f"Exit area: {summary['exit_area_m2']:.4f} m^2")
    print(f"Throat area: {summary['throat_area_m2']:.4f} m^2")
    for warning in summary["warnings"]:
        print(f"Warning: {warning}")

    plot_PV(result, show=False, persist=True)
    plot_TS(result, show=False, persist=True)
    plot_TP(result, show=False, persist=True)
    plot_performance(result, show=False, persist=True)
    plot_engine_flow(result, show=False, persist=True)
    plot_engine_flow(result, ideal=True, show=False, persist=True)

    envelope_df = sweep_flight_envelope(config, [0.0, 4000.0, 8000.0, 12000.0], [50.0, 125.0, 200.0, 275.0, 350.0])
    plot_operating_map(envelope_df, metric="thrust_N", show=False, persist=True)

    exports = export_result_tables(result, summary, output_dir="outputs")
    report_path = write_html_report(summary, exports, output_dir="outputs")
    print(f"Saved report: {report_path.resolve()}")


if __name__ == "__main__":
    main()
