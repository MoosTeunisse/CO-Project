from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict, Dict, List

from models import DayPlan, Instance, RequestPlan, Route, Solution, SolutionSummary


class HeuristicConstructionError(RuntimeError):
    pass


def build_initial_solution(instance: Instance) -> Solution:
    """
    Baseline constructive heuristic.

    Strategy:
    - choose the earliest feasible delivery day for each request,
      while respecting global tool availability over time
    - create one direct delivery route and one direct pickup route per request

    This is intentionally simple. It is a clean starting point that always writes a
    validator-compatible solution when the greedy day assignment succeeds.
    """
    depot = instance.depot_coordinate
    requests_sorted = sorted(
        instance.requests.values(),
        key=lambda r: (r.first_day, r.last_day, r.location_id, r.id),
    )

    # in_use[tool_id][day] = number of tools of that type present at customers on that day
    in_use: Dict[int, List[int]] = {
        tool_id: [0] * (instance.days + 1) for tool_id in instance.tools
    }

    request_plans: Dict[int, RequestPlan] = {}
    day_routes: DefaultDict[int, List[Route]] = defaultdict(list)

    for request in requests_sorted:
        tool = instance.tools[request.tool_id]
        delivery_day = _choose_earliest_feasible_day(instance, request, in_use)
        pickup_day = delivery_day + request.stay_days

        # Reserve tool usage on the customer for each active day.
        for day in range(delivery_day, pickup_day):
            in_use[request.tool_id][day] += request.quantity

        request_plans[request.id] = RequestPlan(
            request_id=request.id,
            delivery_day=delivery_day,
            pickup_day=pickup_day,
        )

        delivery_vehicle_id = len(day_routes[delivery_day]) + 1
        day_routes[delivery_day].append(
            Route(vehicle_id=delivery_vehicle_id, stops=[depot, request.id, depot])
        )

        pickup_vehicle_id = len(day_routes[pickup_day]) + 1
        day_routes[pickup_day].append(
            Route(vehicle_id=pickup_vehicle_id, stops=[depot, -request.id, depot])
        )

        # Defensive route feasibility checks for the starter solution.
        route_distance = 2 * instance.distance_matrix[depot][request.location_id]
        load_size = request.quantity * tool.size
        if route_distance > instance.max_trip_distance:
            raise HeuristicConstructionError(
                f"Direct route for request {request.id} exceeds max trip distance."
            )
        if load_size > instance.capacity:
            raise HeuristicConstructionError(
                f"Request {request.id} exceeds vehicle capacity on a direct route."
            )

    day_plans: Dict[int, DayPlan] = {
        day: DayPlan(day=day, routes=routes)
        for day, routes in sorted(day_routes.items())
    }

    solution = Solution(
        dataset=instance.dataset,
        name=instance.name,
        day_plans=day_plans,
        request_plans=request_plans,
        summary=None,
    )
    solution.summary = compute_solution_summary(instance, solution)
    return solution


def _choose_earliest_feasible_day(
    instance: Instance,
    request,
    in_use: Dict[int, List[int]],
) -> int:
    tool = instance.tools[request.tool_id]
    for delivery_day in range(request.first_day, request.last_day + 1):
        pickup_day = delivery_day + request.stay_days
        feasible = True
        for day in range(delivery_day, pickup_day):
            if in_use[request.tool_id][day] + request.quantity > tool.available:
                feasible = False
                break
        if feasible:
            return delivery_day

    raise HeuristicConstructionError(
        f"Could not assign a delivery day to request {request.id} with this greedy heuristic."
    )


def compute_solution_summary(instance: Instance, solution: Solution) -> SolutionSummary:
    vehicles_per_day = []
    total_distance = 0

    for day_plan in solution.day_plans.values():
        vehicles_per_day.append(len(day_plan.routes))
        for route in day_plan.routes:
            total_distance += route_distance(instance, route.stops)

    max_number_of_vehicles = max(vehicles_per_day, default=0)
    number_of_vehicle_days = sum(vehicles_per_day)

    tool_use = []
    for tool_id, tool in sorted(instance.tools.items()):
        daily = [0] * (instance.days + 1)
        for plan in solution.request_plans.values():
            request = instance.requests[plan.request_id]
            if request.tool_id != tool_id:
                continue
            for day in range(plan.delivery_day, plan.pickup_day):
                daily[day] += request.quantity
        tool_use.append(max(daily))

    tool_cost = sum(
        instance.tools[tool_id].cost * count
        for tool_id, count in zip(sorted(instance.tools.keys()), tool_use)
    )
    cost = (
        instance.vehicle_cost * max_number_of_vehicles
        + instance.vehicle_day_cost * number_of_vehicle_days
        + instance.distance_cost * total_distance
        + tool_cost
    )

    return SolutionSummary(
        max_number_of_vehicles=max_number_of_vehicles,
        number_of_vehicle_days=number_of_vehicle_days,
        tool_use=tool_use,
        distance=total_distance,
        cost=cost,
    )


def route_distance(instance: Instance, stops: List[int]) -> int:
    total = 0
    current_loc = None
    for token in stops:
        if token == 0:
            next_loc = instance.depot_coordinate
        else:
            request_id = abs(token)
            next_loc = instance.requests[request_id].location_id
        if current_loc is not None:
            total += instance.distance_matrix[current_loc][next_loc]
        current_loc = next_loc
    return total
