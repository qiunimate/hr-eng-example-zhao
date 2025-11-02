from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from backend.models import *
from backend.helpers import *
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
    assign_nearest_idle_robot(order)
    log_event("order_created", {"order": order.name, "source": order.source, "target": order.target})
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
async def dashboard() -> str:
    """
    Display real-time AGV fleet dashboard with robots and orders status.
    
    Returns:
        HTML page showing current robot states and order progress
    """
    robots = STATE["robots"]
    orders = STATE["orders"]
    routes = STATE["routes"]
    
    # Create a mapping of node -> list of robots at that node
    node_robots: Dict[str, List[str]] = {}
    for node in GRAPH.nodes:
        node_robots[node] = []
    
    for robot in robots:
        if robot.node in node_robots:
            node_robots[robot.node].append(robot.name)
    
    # SVG layout configuration
    node_positions = {
        "A": (50, 50),
        "B": (150, 50), 
        "C": (250, 50),
        "D": (250, 150),
        "E": (150, 150),
        "F": (50, 150)
    }
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AGV Fleet Dashboard</title>
        <style>
            .dashboard { font-family: Arial, sans-serif; margin: 20px; }
            .container { display: flex; gap: 30px; margin-bottom: 30px; }
            .map-section { flex: 1; }
            .status-section { flex: 1; }
            .svg-map { border: 1px solid #ccc; background: #f9f9f9; }
            .node { fill: #4CAF50; stroke: #2E7D32; stroke-width: 2; }
            .node-text { font-size: 14px; font-weight: bold; fill: white; text-anchor: middle; }
            .edge { stroke: #666; stroke-width: 2; }
            .edge-text { font-size: 12px; fill: #333; }
            .robot { fill: #FF5722; stroke: #D84315; stroke-width: 2; }
            .robot-text { font-size: 10px; fill: white; text-anchor: middle; }
            ul { list-style-type: none; padding: 0; }
            li { margin: 8px 0; padding: 8px; background: #f5f5f5; border-radius: 4px; }
            .idle { color: #4CAF50; }
            .executing { color: #FF5722; }
        </style>
    </head>
    <body>
        <div class="dashboard">
            <h1>🚀 AGV Fleet Dashboard</h1>
            <div class="container">
                <div class="map-section">
                    <h2>Map Visualization</h2>
    """
    
    # SVG Map
    svg_width = 400
    svg_height = 250
    html += f'<svg width="{svg_width}" height="{svg_height}" class="svg-map">'
    
    # Draw edges first (so they appear behind nodes)
    for edge in GRAPH.edges:
        if edge.from_ in node_positions and edge.to in node_positions:
            x1, y1 = node_positions[edge.from_]
            x2, y2 = node_positions[edge.to]
            html += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="edge" />'
            # Edge label (weight)
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            html += f'<text x="{mid_x}" y="{mid_y - 5}" class="edge-text">{edge.weight}</text>'
    
    # Draw nodes
    for node, (x, y) in node_positions.items():
        # Node circle
        html += f'<circle cx="{x}" cy="{y}" r="20" class="node" />'
        # Node label
        html += f'<text x="{x}" y="{y + 5}" class="node-text">{node}</text>'
        
        # Draw robots at this node
        robots_here = node_robots[node]
        for i, robot_name in enumerate(robots_here):
            robot_x = x - 15 + (i * 15)
            robot_y = y - 30
            html += f'<circle cx="{robot_x}" cy="{robot_y}" r="8" class="robot" />'
            html += f'<text x="{robot_x}" y="{robot_y + 3}" class="robot-text">{robot_name}</text>'
    
    html += '</svg>'
    
    # Status sections
    html += """
                </div>
                <div class="status-section">
                    <h2>Robots Status</h2>
                    <ul>
    """
    
    for r in robots:
        status_class = "idle" if r.status == RobotStatus.IDLE else "executing"
        status_icon = "🟢" if r.status == RobotStatus.IDLE else "🔴"
        html += f'<li class="{status_class}">{status_icon} <strong>{r.name}</strong> — {r.status.value} at <strong>{r.node}</strong></li>'
    
    html += """
                    </ul>
                    
                    <h2>Orders</h2>
                    <ul>
    """
    
    for o in orders:
        # icons
        status_icon = {
            OrderStatus.NEW: "🆕",
            OrderStatus.IN_PROGRESS: "🔄", 
            OrderStatus.DONE: "✅",
            OrderStatus.FAILED: "❌"
        }.get(o.status, "❓")

        html += f'<li>{status_icon} <strong>{o.name}</strong>: {o.source} → {o.target} [{o.status.value}]</li>'
    
    # Route section
    html += """
            </ul>
            </div>
            <div class="status-section">
                <h2>Routes</h2>
                <ul>
    """

    for route in routes:
        remaining_path = route.path[route.next_index:]
        html += f'<li><strong>{route.robot}</strong> → Order: <strong>{route.order}</strong> | Remaining path: {" → ".join(remaining_path)}</li>'


    html += """
                </ul>
            </div>
    """
    
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


