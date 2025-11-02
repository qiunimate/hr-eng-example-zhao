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

@app.get("/events", response_model=List[Event])
async def get_events(limit: Optional[int] = None, since: Optional[str] = None):
    """
    Retrieve events, optionally limited and filtered by a 'since' timestamp (ISO 8601).
    """
    events = STATE.get("events", [])

    if since is not None:
        try:
            # Parse 'since' as UTC-aware datetime
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ISO 8601 timestamp for 'since'")
        
        # Filter events, making event times UTC-aware
        filtered_events = []
        for e in events:
            event_time = datetime.fromisoformat(e.time.replace("Z", "+00:00"))
            if event_time > since_dt:
                filtered_events.append(e)
        events = filtered_events

    if limit is not None:
        events = events[-limit:]

    return events[::-1]

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
    return RoutesResponse(routes=STATE.get("routes", []))

@app.post("/tick", tags=["simulation"])
async def tick() -> Dict[str, str]:
    for route in STATE.get("routes", []):
        robot = next(r for r in STATE["robots"] if r.name == route.robot)
        
        # If starting a new edge, initialize remaining_weight
        if route.remaining_weight == 0 and route.next_index < len(route.path) - 1:
            # Find edge weight
            from_node = route.path[route.next_index]
            to_node = route.path[route.next_index + 1]
            edge = next((e for e in GRAPH.edges if 
                         (e.from_ == from_node and e.to == to_node) or 
                         (e.from_ == to_node and e.to == from_node)), None)
            route.remaining_weight = edge.weight if edge else 1

        # Advance robot along the edge
        if route.remaining_weight > 0:
            route.remaining_weight -= 1  # 1 tick passed
            log_event("robot_moving", {"robot": robot.name, "from": robot.node, "to": route.path[route.next_index + 1], "remaining_weight": route.remaining_weight})

        # If edge completed
        if route.remaining_weight <= 0 and route.next_index < len(route.path) - 1:
            route.next_index += 1
            robot.node = route.path[route.next_index]
            log_event("robot_arrived", {"robot": robot.name, "at": robot.node})

        # Route completed
        if route.next_index == len(route.path) - 1:
            robot.status = RobotStatus.IDLE
            order = next(o for o in STATE["orders"] if o.name == route.order)
            order.status = OrderStatus.DONE
            STATE["routes"].remove(route)
            log_event("order_completed", {"order": order.name, "robot": robot.name, "at": robot.node})

    # Assign NEW or FAILED orders
    for order in STATE["orders"]:
        if order.status in {OrderStatus.NEW, OrderStatus.FAILED}:
            assign_nearest_idle_robot(order)
    log_event("tick_processed", {})
    return {"status": "ok"}


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

    # Compute in-flight robot positions (robots currently traversing an edge)
    in_flight_positions: Dict[str, tuple[float, float]] = {}
    for route in routes:
        # route.next_index points at the current node index; if next_index < len(path)-1
        # the robot is traversing from path[next_index] -> path[next_index+1]
        if getattr(route, "remaining_weight", 0) > 0 and route.next_index < len(route.path) - 1:
            from_node = route.path[route.next_index]
            to_node = route.path[route.next_index + 1]
            if from_node in NODE_POSITIONS and to_node in NODE_POSITIONS:
                x1, y1 = NODE_POSITIONS[from_node]
                x2, y2 = NODE_POSITIONS[to_node]
                # find edge weight
                edge = next((e for e in GRAPH.edges if (e.from_ == from_node and e.to == to_node) or (e.from_ == to_node and e.to == from_node)), None)
                edge_w = float(edge.weight) if edge else 1.0
                # compute fraction progressed along edge
                progressed = max(0.0, min(edge_w - float(route.remaining_weight), edge_w))
                frac = progressed / edge_w if edge_w != 0 else 1.0
                rx = x1 + (x2 - x1) * frac
                ry = y1 + (y2 - y1) * frac
                in_flight_positions[route.robot] = (rx, ry)

    # Remove in-flight robots from node lists so they aren't double-drawn at the node
    for robot_name in list(in_flight_positions.keys()):
        for node_list in node_robots.values():
            if robot_name in node_list:
                node_list.remove(robot_name)
    
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
    svg_height = 300
    html += f'<svg width="{svg_width}" height="{svg_height}" class="svg-map">'
    
    # Draw edges first (so they appear behind nodes)
    for edge in GRAPH.edges:
        if edge.from_ in list(NODE_POSITIONS.keys()) and edge.to in list(NODE_POSITIONS.keys()):
            x1, y1 = NODE_POSITIONS[edge.from_]
            x2, y2 = NODE_POSITIONS[edge.to]
            html += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="edge" />'
            # Edge label (weight)
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            html += f'<text x="{mid_x}" y="{mid_y - 5}" class="edge-text">{edge.weight}</text>'
    
    # Draw nodes
    for node, (x, y) in NODE_POSITIONS.items():
        # Node circle
        html += f'<circle cx="{x}" cy="{y}" r="20" class="node" />'
        # Node label
        html += f'<text x="{x}" y="{y + 5}" class="node-text">{node}</text>'
        
        # Draw robots at this node
        robots_here = node_robots[node]
        for i, robot_name in enumerate(robots_here):
            # If this robot is currently in-flight along an edge, skip drawing it at the node
            if robot_name in in_flight_positions:
                continue
            robot_x = x - 15 + (i * 15)
            robot_y = y - 30
            html += f'<circle cx="{robot_x}" cy="{robot_y}" r="8" class="robot" />'
            html += f'<text x="{robot_x}" y="{robot_y + 3}" class="robot-text">{robot_name}</text>'
    
    # Draw in-flight robots (between nodes) inside the same SVG
    for robot_name, (rx, ry) in in_flight_positions.items():
        html += f'<circle cx="{rx}" cy="{ry}" r="8" class="robot" />'
        html += f'<text x="{rx}" y="{ry + 3}" class="robot-text">{robot_name}</text>'

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

    # add auto-refresh script
    html += """
    <script>
    // Reload the entire dashboard every 2 seconds
    setInterval(() => {
        window.location.reload();
    }, 2000);
    </script>
    """
    html += "</div></body></html>"
    
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


