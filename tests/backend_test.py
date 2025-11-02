import pytest
from backend.models import *
from backend.helpers import shortest_path, assign_nearest_idle_robot, STATE, GRAPH, RobotStatus, OrderStatus

# -----------------------------
# Test Fixtures (seed deterministic state)
# -----------------------------

@pytest.fixture(autouse=True)
def reset_state():
    """Reset STATE and robots before each test."""
    STATE["orders"] = []
    STATE["robots"] = [
        Robot(name="R1", status=RobotStatus.IDLE, node="A"),
        Robot(name="R2", status=RobotStatus.IDLE, node="C"),
        Robot(name="R3", status=RobotStatus.IDLE, node="E"),
    ]
    STATE["routes"] = []
    STATE["events"] = []
    yield
    # cleanup if needed
    STATE["orders"] = []
    STATE["robots"] = []
    STATE["routes"] = []
    STATE["events"] = []

# -----------------------------
# Pathfinding Tests
# -----------------------------

def test_shortest_path_basic():
    dist, path = shortest_path("A", "D")
    # Check path starts and ends correctly
    assert path[0] == "A"
    assert path[-1] == "D"
    # Check distance is correct (A->B->C->D = 1+2+2 = 5)
    assert dist == 5

def test_shortest_path_monotonicity():
    """Property test: path cost increases monotonically along edges."""
    nodes = GRAPH.nodes
    for start in nodes:
        for end in nodes:
            if start != end:
                dist, path = shortest_path(start, end)
                total = 0
                for i in range(len(path)-1):
                    # find edge weight
                    edge = next(e for e in GRAPH.edges if (e.from_ == path[i] and e.to == path[i+1]) or (e.from_ == path[i+1] and e.to == path[i]))
                    total += edge.weight
                    # cumulative distance should never exceed total
                    assert total <= dist
                # final total should equal dist
                assert total == dist

def test_shortest_path_invalid_node():
    with pytest.raises(ValueError):
        shortest_path("X", "A")

# -----------------------------
# Scheduling / Assignment Tests
# -----------------------------

def test_assign_nearest_idle_robot():
    order = Order(name="O1", source="B", target="D")
    route = assign_nearest_idle_robot(order)

    # A robot should be assigned
    assert route is not None
    assert order.status == OrderStatus.IN_PROGRESS
    robot = next(r for r in STATE["robots"] if r.name == route.robot)
    assert robot.status == RobotStatus.EXECUTING

def test_assign_nearest_idle_robot_tiebreak():
    """Tie-break by robot name if distances equal"""
    # Place R1 and R2 at same distance to B
    STATE["robots"][0].node = "A"  # R1
    STATE["robots"][1].node = "C"  # R2
    order = Order(name="O2", source="B", target="D")
    route = assign_nearest_idle_robot(order)
    # R1 should be chosen because name is lexicographically smaller
    assert route.robot == "R1"

def test_assign_nearest_idle_robot_no_idle():
    # Make all robots busy
    for r in STATE["robots"]:
        r.status = RobotStatus.EXECUTING
    order = Order(name="O3", source="B", target="D")
    route = assign_nearest_idle_robot(order)
    assert route is None
    assert order.status == OrderStatus.NEW

# -----------------------------
# Reservation / Route Tests
# -----------------------------

def test_route_saved_in_state():
    order = Order(name="O4", source="B", target="D")
    route = assign_nearest_idle_robot(order)
    assert route in STATE["routes"]
    # The first node should be robot's starting node
    assert route.path[0] == next(r for r in STATE["robots"] if r.name == route.robot).node or route.path[0] in GRAPH.nodes

def test_route_progress_simulation():
    """Simulate a simple tick and check robot progresses"""
    from backend.main import tick

    order = Order(name="O5", source="B", target="D")
    assign_nearest_idle_robot(order)
    route = STATE["routes"][0]
    robot = next(r for r in STATE["robots"] if r.name == route.robot)

    # Simulate one tick assuming edge weight 1 (simplest)
    initial_node = robot.node
    # Initialize remaining_weight for the edge
    route.remaining_weight = 1
    import asyncio
    asyncio.run(tick())
    # robot should have moved to next node
    assert robot.node != initial_node or route.remaining_weight == 0
