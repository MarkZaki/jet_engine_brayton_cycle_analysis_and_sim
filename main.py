from performance.metrics import summarize_result
from performance.reporting import export_result_tables, write_html_report
from solver.engine import run_engine_case
from visualization.plots import plot_PV, plot_TP, plot_TS, plot_engine_flow, plot_performance


def main():
    result = run_engine_case()
    summary = summarize_result(result, V0=result.config["flight_speed"])

    print("---- BRAYTON CYCLE RESULTS ----")
    print(f"Thrust: {summary['thrust_N']:.2f} N")
    print(f"Specific thrust: {summary['specific_thrust_N_per_kg_s']:.2f} N/(kg/s)")
    print(f"Fuel-air ratio: {summary['fuel_air_ratio']:.5f}")
    print(f"Fuel flow: {summary['fuel_flow_kg_s']:.4f} kg/s")
    print(f"Specific impulse: {summary['specific_impulse_s']:.2f} s")
    print(f"Thermal efficiency: {summary['thermal_efficiency']:.4f}")
    print(f"Propulsive efficiency: {summary['propulsive_efficiency']:.4f}")
    print(f"Overall efficiency: {summary['overall_efficiency']:.4f}")
    print(f"Back work ratio: {summary['bwr']:.4f}")
    print(f"Nozzle choked: {summary['nozzle_choked']}")
    print(f"Exit Mach: {summary['exit_mach']:.3f}")
    for warning in summary["warnings"]:
        print(f"Warning: {warning}")

    plot_PV(result, show=False, persist=True)
    plot_TS(result, show=False, persist=True)
    plot_TP(result, show=False, persist=True)
    plot_performance(result, show=False, persist=True)
    plot_engine_flow(result, show=False, persist=True)
    plot_engine_flow(result, ideal=True, show=False, persist=True)

    exports = export_result_tables(result, summary, output_dir="outputs")
    report_path = write_html_report(
        summary,
        exports,
        output_dir="outputs",
        config=result.config,
        assumptions=result.assumptions,
        equations=result.equations,
    )
    print(f"Saved report: {report_path.resolve()}")


if __name__ == "__main__":
    main()
