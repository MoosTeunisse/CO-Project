from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Tool:
    id: int
    size: int
    available: int
    cost: int


@dataclass(frozen=True)
class Coordinate:
    id: int
    x: int
    y: int


@dataclass(frozen=True)
class Request:
    id: int
    location_id: int
    first_day: int
    last_day: int
    stay_days: int
    tool_id: int
    quantity: int

    @property
    def pickup_day_offset(self) -> int:
        return self.stay_days


@dataclass
class Instance:
    dataset: str
    name: str
    days: int
    capacity: int
    max_trip_distance: int
    depot_coordinate: int
    vehicle_cost: int
    vehicle_day_cost: int
    distance_cost: int
    tools: Dict[int, Tool]
    coordinates: Dict[int, Coordinate]
    requests: Dict[int, Request]
    distance_matrix: List[List[int]]


@dataclass
class Route:
    vehicle_id: int
    stops: List[int]


@dataclass
class DayPlan:
    day: int
    routes: List[Route] = field(default_factory=list)


@dataclass
class RequestPlan:
    request_id: int
    delivery_day: int
    pickup_day: int


@dataclass
class SolutionSummary:
    max_number_of_vehicles: int
    number_of_vehicle_days: int
    tool_use: List[int]
    distance: int
    cost: int


@dataclass
class Solution:
    dataset: str
    name: str
    day_plans: Dict[int, DayPlan]
    request_plans: Dict[int, RequestPlan]
    summary: Optional[SolutionSummary] = None
