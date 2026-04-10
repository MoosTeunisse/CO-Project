from __future__ import annotations

import math
from typing import Dict, List, Optional, TextIO

from models import Coordinate, Instance, Request, Tool


class InstanceParseError(ValueError):
    pass


class LineReader:
    def __init__(self, fh: TextIO):
        self._fh = fh

    def next_nonempty(self) -> str:
        for raw in self._fh:
            line = raw.strip()
            if line:
                return line
        raise InstanceParseError("Unexpected end of file while reading instance.")


def _read_assignment(reader: LineReader, key: str) -> str:
    line = reader.next_nonempty()
    pieces = line.split("=", 1)
    if len(pieces) != 2:
        raise InstanceParseError(f"Expected assignment for {key!r}, found: {line}")
    lhs, rhs = pieces[0].strip(), pieces[1].strip()
    if lhs != key:
        raise InstanceParseError(f"Expected key {key!r}, found {lhs!r}")
    return rhs


def _parse_int_assignment(reader: LineReader, key: str) -> int:
    value = _read_assignment(reader, key)
    try:
        return int(value)
    except ValueError as exc:
        raise InstanceParseError(f"Expected integer for {key}, found: {value}") from exc


def _euclidean_floor(a: Coordinate, b: Coordinate) -> int:
    return math.floor(math.hypot(a.x - b.x, a.y - b.y))


def _build_distance_matrix(coords: Dict[int, Coordinate]) -> List[List[int]]:
    n = len(coords)
    if set(coords.keys()) != set(range(n)):
        raise InstanceParseError("Coordinate IDs must be consecutive and start at 0.")
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = _euclidean_floor(coords[i], coords[j])
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


def read_instance(path: str) -> Instance:
    with open(path, "r", encoding="utf-8") as fh:
        reader = LineReader(fh)

        dataset = _read_assignment(reader, "DATASET")
        name = _read_assignment(reader, "NAME")

        days = _parse_int_assignment(reader, "DAYS")
        capacity = _parse_int_assignment(reader, "CAPACITY")
        max_trip_distance = _parse_int_assignment(reader, "MAX_TRIP_DISTANCE")
        depot_coordinate = _parse_int_assignment(reader, "DEPOT_COORDINATE")

        vehicle_cost = _parse_int_assignment(reader, "VEHICLE_COST")
        vehicle_day_cost = _parse_int_assignment(reader, "VEHICLE_DAY_COST")
        distance_cost = _parse_int_assignment(reader, "DISTANCE_COST")

        num_tools = _parse_int_assignment(reader, "TOOLS")
        tools: Dict[int, Tool] = {}
        for expected_id in range(1, num_tools + 1):
            line = reader.next_nonempty()
            parts = line.split()
            if len(parts) != 4:
                raise InstanceParseError(f"Expected 4 integers on tool line, found: {line}")
            tool_id, size, available, cost = map(int, parts)
            if tool_id != expected_id:
                raise InstanceParseError(
                    f"Tool IDs must be consecutive starting at 1. Expected {expected_id}, found {tool_id}."
                )
            tools[tool_id] = Tool(tool_id, size, available, cost)

        num_coordinates = _parse_int_assignment(reader, "COORDINATES")
        coordinates: Dict[int, Coordinate] = {}
        for expected_id in range(num_coordinates):
            line = reader.next_nonempty()
            parts = line.split()
            if len(parts) != 3:
                raise InstanceParseError(f"Expected 3 integers on coordinate line, found: {line}")
            loc_id, x, y = map(int, parts)
            if loc_id != expected_id:
                raise InstanceParseError(
                    f"Coordinate IDs must be consecutive starting at 0. Expected {expected_id}, found {loc_id}."
                )
            coordinates[loc_id] = Coordinate(loc_id, x, y)

        num_requests = _parse_int_assignment(reader, "REQUESTS")
        requests: Dict[int, Request] = {}
        for expected_id in range(1, num_requests + 1):
            line = reader.next_nonempty()
            parts = line.split()
            if len(parts) != 7:
                raise InstanceParseError(f"Expected 7 integers on request line, found: {line}")
            request_id, location_id, first_day, last_day, stay_days, tool_id, quantity = map(int, parts)
            if request_id != expected_id:
                raise InstanceParseError(
                    f"Request IDs must be consecutive starting at 1. Expected {expected_id}, found {request_id}."
                )
            if location_id not in coordinates:
                raise InstanceParseError(f"Request {request_id} refers to unknown location {location_id}.")
            if tool_id not in tools:
                raise InstanceParseError(f"Request {request_id} refers to unknown tool {tool_id}.")
            if not (1 <= first_day <= last_day <= days):
                raise InstanceParseError(f"Request {request_id} has invalid delivery window.")
            if stay_days <= 0:
                raise InstanceParseError(f"Request {request_id} has non-positive stay_days.")
            if last_day + stay_days > days:
                raise InstanceParseError(
                    f"Request {request_id} would require pickup after the planning horizon."
                )
            if quantity <= 0:
                raise InstanceParseError(f"Request {request_id} has non-positive quantity.")
            requests[request_id] = Request(
                id=request_id,
                location_id=location_id,
                first_day=first_day,
                last_day=last_day,
                stay_days=stay_days,
                tool_id=tool_id,
                quantity=quantity,
            )

        maybe_next: Optional[str]
        try:
            maybe_next = reader.next_nonempty()
        except InstanceParseError:
            maybe_next = None

        distance_matrix: List[List[int]]
        if maybe_next is None:
            distance_matrix = _build_distance_matrix(coordinates)
        elif maybe_next == "DISTANCE":
            distance_matrix = []
            for _ in range(num_coordinates):
                line = reader.next_nonempty()
                row = list(map(int, line.split()))
                if len(row) != num_coordinates:
                    raise InstanceParseError(
                        f"Distance row should have {num_coordinates} values, found {len(row)}."
                    )
                distance_matrix.append(row)
        else:
            raise InstanceParseError(f"Unexpected trailing line after requests: {maybe_next}")

    instance = Instance(
        dataset=dataset,
        name=name,
        days=days,
        capacity=capacity,
        max_trip_distance=max_trip_distance,
        depot_coordinate=depot_coordinate,
        vehicle_cost=vehicle_cost,
        vehicle_day_cost=vehicle_day_cost,
        distance_cost=distance_cost,
        tools=tools,
        coordinates=coordinates,
        requests=requests,
        distance_matrix=distance_matrix,
    )
    validate_instance_basics(instance)
    return instance


def validate_instance_basics(instance: Instance) -> None:
    depot = instance.depot_coordinate
    if depot not in instance.coordinates:
        raise InstanceParseError(f"Depot coordinate {depot} not found in coordinates.")

    for request in instance.requests.values():
        tool = instance.tools[request.tool_id]
        trip_distance = 2 * instance.distance_matrix[depot][request.location_id]
        if trip_distance > instance.max_trip_distance:
            raise InstanceParseError(
                f"Request {request.id} cannot be served even by a direct out-and-back route: distance {trip_distance} exceeds max_trip_distance {instance.max_trip_distance}."
            )
        load_size = request.quantity * tool.size
        if load_size > instance.capacity:
            raise InstanceParseError(
                f"Request {request.id} cannot be served by one vehicle: load size {load_size} exceeds capacity {instance.capacity}."
            )
