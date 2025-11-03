
# Ask
Choose one of the two components (frontend, backend) and choose a task. 
You can create an implementation or a design description.
If you choose to use AI Agents or Copilot, please highlight your prompts and thought process.
Send your contribution before the in-person meeting. We will talk about your solution.
There is no right or wrong. We are curious about problem solving capabilities.

# Backend

## Task:
Choose 3-5

[x] Scheduler (nearest-idle): Implement assign_nearest_idle_robot(order) using shortest-path to the order’s source, tie-break by robot name; flip statuses (NEW→IN_PROGRESS, robot IDLE→EXECUTING) and store the planned route.

[x] Pathfinding: Add Dijkstra/A* over the provided graph (bidirectional edges, weight as cost). Return both distance and path.

[x] Tick simulation: POST /tick advances time by one “step”; robots move one edge per tick, update their node; when reaching target, mark order DONE, robot IDLE.

[x] State & validation: Validate nodes exist; keep state in memory; guard against duplicate order names; return helpful 4xx errors.

[x] OpenAPI polish: Ensure models/enums are documented; add tags and examples; verify with /docs.

[x] Deterministic tests: Unit tests for pathfinding, scheduling, and reservations; seed test graph/robots; use property tests for “path cost monotonicity”.


#### Nice-to-haves

[] Collision avoidance (edge reservations): Prevent two robots from occupying the same edge in the same tick; simple time-slot reservation is enough (defer one robot if conflict).

[x] Batch scheduling: On each tick, try to assign all NEW orders (recompute as robots free up).

[] Preemption guardrails: Don’t reassign an order already IN_PROGRESS; allow manual cancellation path to set FAILED.

[x] Audit log: Append events (order created/assigned/finished, robot moved) and expose GET /events?since=…&limit=….

#### Stretch goals

[] Charging logic: Add battery (0–100). Drain per tick; when <20%, send to nearest “charger” node; pause scheduling while charging; resume at >80%.

[] Priorities & SLAs: Orders get priority (int) and optional deadline. Scheduler prefers higher priority, then nearest distance; mark FAILED if deadline exceeded.

[] Zones/blocked edges: Support temporarily blocked edges (maintenance) and zone constraints (e.g., robots with capability: {zone: 'cold'} only).

[] Persistence: Swap in SQLite or TinyDB; add /reset to re-seed for tests.

[] WebSocket/SSE: Push robot/ order updates instead of polling; keep /tick but notify subscribers.

#### Advanced stretch (even spicier)

[] Multi-robot routing for one order: Allow a handoff midway (e.g., pallet handover node) and show the selection logic.

[] Heuristic tuning: Pluggable cost function (e.g., penalize congestion, prefer wider edges); expose GET /metrics (avg wait time, utilization).

[] Idempotency & concurrency: Make POST /addOrder idempotent via Idempotency-Key; protect scheduler with a lock to avoid race conditions under parallel ticks.

[] Explainability endpoint: GET /explain/assignments/{order} returns the decision tree (distances considered, tie-breaks, constraints causing rejections).

[] Replay & time travel: Record ticks and allow POST /replay?from=…&to=… to rebuild state; great for tests and demos.

## Acceptance:

[x]App loads graph and lists robots + orders.
[x]Adding an order triggers scheduling when an IDLE robot exists.
[x]Robots visibly move along paths over time; orders progress to DONE.
[x]No runtime errors; basic empty/error states handled.

# Frontend

Build a small React app that:

- Visualizes the map
- Render nodes and edges (simple 2D layout is fine; a grid or force layout is OK).
- Show robots on their current nodes; color by status (IDLE vs EXECUTING).
- Draw a polyline for each robot’s current route (if executing).

- Shows operational panels

  - Orders panel: list all orders, status chips, assigned robot (if any).
  - Robots panel: list robots with status and current node.
  - Add Order form: inputs name, source, target → calls POST /addOrder.

- Implements client-side scheduling + simulation

- On every tick (e.g., setInterval), pull /getOrders, /getRobots, /getGraph.


UX niceties (lightweight)

- Disable “Add” if source or target not in graph.

- Tooltips for nodes/edges/robots.

- Simple legends for colors.

### Hints

If you prefer, you can mock the API with a local in-memory service layer—just keep the interfaces the same.

# Probable Questions
- What challenges do you foresee and why?
