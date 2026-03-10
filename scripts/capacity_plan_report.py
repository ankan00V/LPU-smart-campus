#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _bootstrap import PROJECT_ROOT
from app.performance import build_capacity_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate capacity planning report from live SLA samples")
    parser.add_argument("--window-minutes", type=int, default=15)
    parser.add_argument("--expected-peak-rps", type=float, default=0.0)
    parser.add_argument("--growth-percent", type=float, default=30.0)
    parser.add_argument("--safety-factor", type=float, default=1.3)
    parser.add_argument("--output", default="", help="Optional JSON output file path")
    args = parser.parse_args()

    report = build_capacity_plan(
        window_minutes=max(1, int(args.window_minutes)),
        expected_peak_rps=(float(args.expected_peak_rps) if args.expected_peak_rps > 0 else None),
        growth_percent=float(args.growth_percent),
        safety_factor=float(args.safety_factor),
    )
    if args.output:
        output_path = Path(args.output).expanduser()
        if not output_path.is_absolute():
            output_path = (PROJECT_ROOT / output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"written_to": str(output_path), "recommended_nodes": report["recommended_nodes"]}, indent=2))
        return
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
