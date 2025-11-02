from typing import List, Dict, Optional, Tuple
from backend.models import GRAPH
import heapq

# -----------------------------
# Pathfinding
# -----------------------------

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