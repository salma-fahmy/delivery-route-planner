#!/usr/bin/env python3
"""Delivery Route Planner - command line entry point.

Examples:
    python main.py data/sample_deliveries.csv
    python main.py data/sample_deliveries.csv --capacity 8
    python main.py data/edge_cases.csv --json plan.json
    python main.py data/sample_deliveries.csv --simulate 6,8,10,12
"""

import argparse
import json
import sys

from planner.loader import load_deliveries
from planner.planner import DEFAULT_CAPACITY, plan_trips
from planner.report import format_fleet_simulation, format_plan, plan_to_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Group delivery requests into vehicle trips.")
    parser.add_argument("input", help="path to the deliveries file (.csv or .json)")
    parser.add_argument("--capacity", type=float, default=DEFAULT_CAPACITY,
                        help=f"vehicle capacity in kg (default: {DEFAULT_CAPACITY:g})")
    parser.add_argument("--json", metavar="PATH", help="also write the plan as JSON to PATH")
    parser.add_argument("--no-consolidate", action="store_true",
                        help="keep every trip inside a single area, even half empty ones")
    parser.add_argument("--simulate", metavar="LIST",
                        help="comma separated capacities to compare, e.g. 6,8,10,12")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        deliveries, rejected = load_deliveries(args.input)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.capacity <= 0:
        print("Error: --capacity must be greater than 0", file=sys.stderr)
        return 1

    result = plan_trips(deliveries, capacity=args.capacity,
                        consolidate=not args.no_consolidate)

    print(format_plan(result, rejected))

    if args.simulate:
        try:
            capacities = [float(value) for value in args.simulate.split(",") if value.strip()]
        except ValueError:
            print("Error: --simulate expects numbers, e.g. 6,8,10,12", file=sys.stderr)
            return 1
        print()
        print(format_fleet_simulation(deliveries, capacities))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(plan_to_dict(result, rejected), handle, indent=2, ensure_ascii=False)
        print(f"\nJSON plan written to {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
