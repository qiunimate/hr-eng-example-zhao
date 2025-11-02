from typing import List, Dict, Optional, Tuple
from backend.models import *
import heapq
from datetime import datetime

# path finding
def shortest_path(start: str, goal: str) -> tuple[float, list[str]]:
    nodes = set(GRAPH.nodes)
    if start not in nodes or goal not in nodes:
        raise ValueError("start/goal must be valid graph nodes")

    # construct adjacency list
    adj = {}
    for e in GRAPH.edges:
        adj.setdefault(e.from_, []).append((e.to, e.weight))
        adj.setdefault(e.to, []).append((e.from_, e.weight))  # bidirectional

    heap = [(0.0, start, [start])]  # (distance, current_node, path)
    visited = {}

    while heap:
        dist, node, path = heapq.heappop(heap)
        if node in visited:
            continue
        visited[node] = dist
        if node == goal:
            return dist, path
        for nbr, w in adj.get(node, []):
            if nbr not in visited:
                heapq.heappush(heap, (dist + float(w), nbr, path + [nbr]))

    raise ValueError(f"No path from {start} to {goal}")

# robot assignment
def assign_nearest_idle_robot(order: Order) -> Optional[Route]:
    """
    - assign_nearest_idle_robot finds the nearest IDLE robot to the order's source node,
    - if same distance, tie-break by robot.name
    - updates robot and order status
    - saves route for tick simulation
    """
    # Find all idle robots
    idle_robots = [r for r in STATE["robots"] if r.status == RobotStatus.IDLE]
    if not idle_robots:
        # No idle robots available
        return None

    best_robot = None
    best_distance = float("inf")
    path_to_source = None

    for r in idle_robots:
        try:
            dist, path = shortest_path(r.node, order.source)
        except ValueError:
            continue  # No path to source
        if dist < best_distance or (dist == best_distance and (best_robot is None or r.name < best_robot.name)):
            best_robot = r
            best_distance = dist
            path_to_source = path

    if best_robot is None:
        # No robot can reach the order's source node
        return None

    # Path from source to target
    _, path_source_to_target = shortest_path(order.source, order.target)
    # Combine full path (avoiding duplicate source node)
    full_path = path_to_source + path_source_to_target[1:]

    # Update statuses
    best_robot.status = RobotStatus.EXECUTING
    order.status = OrderStatus.IN_PROGRESS

    # Save route for tick simulation
    route = Route(robot=best_robot.name, path=full_path, order=order.name)
    STATE["routes"].append({"route": route, "next_index": 0})
    return route

# logger
def log_event(type_: str, detail: dict):
    STATE["events"].append(Event(time=datetime.utcnow().isoformat() + "Z", type=type_, detail=detail))