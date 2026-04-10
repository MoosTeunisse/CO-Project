from __future__ import annotations

import argparse
import os
import sys

from heuristic import HeuristicConstructionError, build_initial_solution
from instance_parser import InstanceParseError, read_instance
from solution_writer import write_solution_txt


def default_output_path(instance_path: str) -> str:
    base, ext = os.path.splitext(instance_path)
    if ext.lower() == ".txt":
        return f"{base}sol.txt"
    return f"{instance_path}_sol.txt"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Starter solver for the CO vehicle routing case."
    )
    parser.add_argument("instance_file", help="Path to the input instance .txt file")
    parser.add_argument(
        "-o",
        "--output",
        help="Output solution file path. Defaults to <instance>sol.txt",
    )
    args = parser.parse_args()

    output_path = args.output or default_output_path(args.instance_file)

    try:
        instance = read_instance(args.instance_file)
        solution = build_initial_solution(instance)
        write_solution_txt(solution, output_path, write_summary=True)
    except (InstanceParseError, HeuristicConstructionError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote solution to: {output_path}")
    if solution.summary is not None:
        print(f"Max vehicles: {solution.summary.max_number_of_vehicles}")
        print(f"Vehicle-days: {solution.summary.number_of_vehicle_days}")
        print(f"Distance: {solution.summary.distance}")
        print(f"Cost: {solution.summary.cost}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
