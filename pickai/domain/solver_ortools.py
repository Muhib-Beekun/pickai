from __future__ import annotations

from typing import Callable

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


Point = tuple[float, float]


def solve_pick_path_tsp(
    locations: list[Point],
    depot: Point,
    distance_fn: Callable[[Point, Point], float],
) -> list[Point]:
    """Solve a single-vehicle TSP tour with OR-Tools and return ordered pick locations."""
    if not locations:
        return []

    points = [depot, *locations]
    n = len(points)

    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_fn(points[from_node], points[to_node]) * 1000)

    transit_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_index)

    search = pywrapcp.DefaultRoutingSearchParameters()
    search.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search.time_limit.seconds = 5

    solution = routing.SolveWithParameters(search)
    if solution is None:
        return locations

    ordered: list[Point] = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        node = manager.IndexToNode(idx)
        if node != 0:
            ordered.append(points[node])
        idx = solution.Value(routing.NextVar(idx))

    return ordered
