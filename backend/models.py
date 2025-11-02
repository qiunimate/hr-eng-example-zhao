from typing import List, Dict, Optional
from enum import Enum

from pydantic import BaseModel, Field

# -----------------------------
# Domain Models (Pydantic)
# -----------------------------

class RobotStatus(str, Enum):
    IDLE = "IDLE"
    EXECUTING = "EXECUTING"

class OrderStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"

class Robot(BaseModel):
    name: str
    status: RobotStatus
    node: str

class Order(BaseModel):
    name: str
    source: str
    target: str
    status: OrderStatus = OrderStatus.NEW

class Edge(BaseModel):
    from_: str = Field(alias="from")
    to: str
    weight: float = 1.0

    class Config:
        allow_population_by_field_name = True
        json_encoders = {RobotStatus: lambda s: s.value, OrderStatus: lambda s: s.value}

class Graph(BaseModel):
    nodes: List[str]
    edges: List[Edge]

class Route(BaseModel):
    robot: str
    next_index: int  # index of next node in path to move to
    order: str
    path: List[str]  # sequence of node names
    remaining_weight: float = 0  # ticks left to finish current edge

class RoutesResponse(BaseModel):
    routes: List[Route]

class Event(BaseModel):
    time: str
    type: str
    detail: dict

# -----------------------------
# API Schemas
# -----------------------------

class AddOrderRequest(BaseModel):
    name: str
    source: str
    target: str

# Optional: include computed assignment in future
class OrdersResponse(BaseModel):
    orders: List[Order]

class RobotsResponse(BaseModel):
    robots: List[Robot]

# -----------------------------
# In-memory State (Replace with DB for prod)
# -----------------------------

STATE: Dict[str, List] = {
    "orders": [],
    "robots": [],
    "routes": [],
    "events": [],
}

GRAPH: Graph = Graph(
    nodes=["A", "B", "C", "D", "E", "F"],
    edges=[
        Edge(**{"from": "A", "to": "B", "weight": 1}),
        Edge(**{"from": "B", "to": "C", "weight": 2}),
        Edge(**{"from": "C", "to": "D", "weight": 2}),
        Edge(**{"from": "B", "to": "E", "weight": 3}),
        Edge(**{"from": "E", "to": "F", "weight": 1}),
        Edge(**{"from": "D", "to": "F", "weight": 2}),
        # Treat edges as undirected for simplicity; callers may add both directions explicitly if desired
    ],
)

SEED_ROBOTS = [
    Robot(name="R1", status=RobotStatus.IDLE, node="A"),
    Robot(name="R2", status=RobotStatus.EXECUTING, node="C"),
    Robot(name="R3", status=RobotStatus.IDLE, node="E"),
]

SEED_ORDERS = [
    Order(name="O-1001", source="B", target="D", status=OrderStatus.NEW),
]