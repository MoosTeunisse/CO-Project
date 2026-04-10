from __future__ import annotations

from models import Solution


def write_solution_txt(solution: Solution, path: str, write_summary: bool = True) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"DATASET = {solution.dataset}\n")
        fh.write(f"NAME = {solution.name}\n\n")

        if write_summary and solution.summary is not None:
            fh.write(f"MAX_NUMBER_OF_VEHICLES = {solution.summary.max_number_of_vehicles}\n")
            fh.write(f"NUMBER_OF_VEHICLE_DAYS = {solution.summary.number_of_vehicle_days}\n")
            fh.write("TOOL_USE = " + " ".join(map(str, solution.summary.tool_use)) + "\n")
            fh.write(f"DISTANCE = {solution.summary.distance}\n")
            fh.write(f"COST = {solution.summary.cost}\n\n")

        for day in sorted(solution.day_plans.keys()):
            day_plan = solution.day_plans[day]
            fh.write(f"DAY = {day_plan.day}\n")
            fh.write(f"NUMBER_OF_VEHICLES = {len(day_plan.routes)}\n")
            for route in day_plan.routes:
                route_str = " ".join(map(str, route.stops))
                fh.write(f"{route.vehicle_id} R {route_str}\n")
            fh.write("\n")
