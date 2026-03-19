import json
from pathlib import Path

import pandas as pd


def _summary_frame(summary):
    return pd.DataFrame(
        [{"metric": key, "value": value} for key, value in summary.items()]
    )


def export_result_tables(result, summary, output_dir="outputs"):
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    station_path = output_path / "station_summary.csv"
    component_path = output_path / "component_summary.csv"
    summary_csv_path = output_path / "summary_metrics.csv"
    summary_json_path = output_path / "summary_metrics.json"

    result.to_dataframe().to_csv(station_path, index=False)
    result.to_component_dataframe().to_csv(component_path, index=False)
    _summary_frame(summary).to_csv(summary_csv_path, index=False)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "station_csv": station_path,
        "component_csv": component_path,
        "summary_csv": summary_csv_path,
        "summary_json": summary_json_path,
    }


def build_html_report(summary, table_exports):
    metric_rows = "\n".join(
        f"<tr><td>{key}</td><td>{value}</td></tr>" for key, value in summary.items()
    )
    export_rows = "\n".join(
        f"<li><a href=\"{path.name}\">{label}</a></li>" for label, path in table_exports.items()
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Jet Engine Cycle Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; background: #F6F8FB; color: #102A43; }}
    h1 {{ margin-bottom: 0.4rem; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 720px; background: #FFFFFF; }}
    th, td {{ border: 1px solid #D9E2EC; padding: 0.65rem 0.8rem; text-align: left; }}
    th {{ background: #E8EFF6; }}
    .card {{ background: #FFFFFF; border-radius: 14px; padding: 1.2rem 1.4rem; margin-top: 1rem; }}
    a {{ color: #0F6CBD; }}
  </style>
</head>
<body>
  <h1>Jet Engine Brayton Cycle Report</h1>
  <p>Generated from the current engine configuration.</p>
  <div class="card">
    <h2>Summary Metrics</h2>
    <table>
      <thead><tr><th>Metric</th><th>Value</th></tr></thead>
      <tbody>
        {metric_rows}
      </tbody>
    </table>
  </div>
  <div class="card">
    <h2>Exported Tables</h2>
    <ul>
      {export_rows}
    </ul>
  </div>
</body>
</html>
"""


def write_html_report(summary, table_exports, output_dir="outputs"):
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    report_path = output_path / "report.html"
    report_path.write_text(build_html_report(summary, table_exports), encoding="utf-8")
    return report_path
