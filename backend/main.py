from enum import Enum
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import HTMLResponse

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

# -----------------------------
# App Setup
# -----------------------------

app = FastAPI(
    title="AGV Scheduling Exercise API",
    version="0.1.0",
    description=(
        "Minimal backend stubs for the AGV fleet scheduling exercise.\n\n"
        "Endpoints provided: /addOrder, /getOrders, /getGraph, /getRobots.\n"
        "State is in-memory and resets on restart."
    ),
)

# CORS for local dev frontends (Vite/Next/CRA)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # CRA/Next.js
        "*",  # loosen for exercise; tighten for prod
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Helpers
# -----------------------------

def _graph_nodes_set() -> set:
    return set(GRAPH.nodes)

# -----------------------------
# Lifecycle
# -----------------------------

@app.on_event("startup")
async def seed_state() -> None:
    # Seed only once per process start
    STATE["orders"] = list(SEED_ORDERS)
    STATE["robots"] = list(SEED_ROBOTS)

# -----------------------------
# Endpoints (as specified)
# -----------------------------

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.post("/addOrder", response_model=Order, tags=["orders"])
async def add_order(req: AddOrderRequest) -> Order:
    # Validate nodes exist in graph
    nodes = _graph_nodes_set()
    if req.source not in nodes or req.target not in nodes:
        raise HTTPException(status_code=400, detail="source/target must be valid graph nodes")

    # Enforce unique order name for simplicity
    if any(o.name == req.name for o in STATE["orders"]):
        raise HTTPException(status_code=409, detail="Order with this name already exists")

    order = Order(name=req.name, source=req.source, target=req.target, status=OrderStatus.NEW)
    STATE["orders"].append(order)
    return order

@app.get("/getOrders", response_model=OrdersResponse, tags=["orders"])
async def get_orders() -> OrdersResponse:
    return OrdersResponse(orders=STATE["orders"])

@app.get("/getRobots", response_model=RobotsResponse, tags=["robots"])
async def get_robots() -> RobotsResponse:
    return RobotsResponse(robots=STATE["robots"])

@app.get("/getGraph", response_model=Graph, tags=["graph"])
async def get_graph() -> Graph:
    return GRAPH

# -----------------------------
# Optional: additional stubs to support simulation (Frontend can ignore)
# -----------------------------

class Route(BaseModel):
    robot: str
    path: List[str]  # sequence of node ids

class RoutesResponse(BaseModel):
    routes: List[Route]

# NOTE: These are *stubs* for stretch goals; they currently return empty data.
@app.get("/routes", response_model=RoutesResponse, tags=["simulation"])
async def get_routes() -> RoutesResponse:
    # TODO: Fill with planned paths once a scheduler is implemented server-side
    return RoutesResponse(routes=[])

@app.post("/tick", tags=["simulation"])
async def tick() -> Dict[str, str]:
    # TODO: Advance in-memory simulation: move robots along paths, update order/robot status
    return {"status": "ok", "note": "tick advanced (no-op stub)"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    robots = STATE["robots"]
    orders = STATE["orders"]
    html = "<h1>AGV Fleet Dashboard</h1>"
    html += "<h2>Robots</h2><ul>"
    for r in robots:
        html += f"<li>{r.name} — {r.status} at {r.node}</li>"
    html += "</ul><h2>Orders</h2><ul>"
    for o in orders:
        html += f"<li>{o.name}: {o.source} → {o.target} [{o.status}]</li>"
    html += "</ul>"
    return html
# -----------------------------
# Run (if executed directly)
# -----------------------------

# Use: uvicorn main:app --reload // or python -m uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
