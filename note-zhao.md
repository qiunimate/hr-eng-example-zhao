# Challenge

## Description
In this file notes the steps and strategies used to solve the challenge.

## Backend challenge
The reason I started with backend challenge is that it is mainly in python. I can spend more time in solving the problem and show you my thought process instead of configuration etc.

### 1. Comprehension and configuration
The first step is to read the README, instruction email and the provided code.


```text
# Prompt 1: Context interpretation:
Here are the context email and README.md of a interview challenge. Summarize the requirements and tasks for the backend component. Also how do you suggest me to complete this challenge effectively?

# Prompt 2: Code interpretation
Here is the python file (main.py), please analyze its functionality and structure. Summarize the main components and their interactions.

# Prompt 3: Setup
How to set up the provided codebase for local development and testing? Please provide step-by-step instructions.
```

### 2. Problem solving

#### 2.0 Plan & overall strategy
We need to figure out what is the best order to implement the features. So that we have a working system as soon as possible, and then we can iterate on it. 

So here is my plan:
1. Dashboard + State & validation
2. Pathfinding (Dijkstra's algorithm)
3. Scheduler (nearest-idle)
4. Tick simulation
5. OpenAPI polish + Deterministic tests
6. to be continued...

Overall strategy:
```text
for all the functions, write doc string and comments to explain the logic.
```

#### 2.1 Dashboard

The first step is to get a dashboard which display current robots and orders status. This is important because it helps to visualize the current state of the system and verify the correctness of the implementation. 

```text
I want to firstly create a dashboard page to visualize essential information as said in the acceptance:

- App loads graph and lists robots + orders.

Please also add doc string for each function you create.
```

#### 2.2 Path finding algorithm
The second step is to implement the path finding algorithm, which can be used by the scheduler to assign the nearest idle robot to an order. 

```text
please implement an algorithm for path finding. The function should take in a start node and a goal node, and return the shortest distance and the path taken. 

Also add doc string and comments explaining the logic.
```

#### 2.3 Scheduler

The third step is to implement the scheduler, which assigns the nearest idle robot to an order. 
The class Route including robot name, next index, path and order name is created to store the planned route, and also display in the dashboard.

There is a problem that if an order is created but there is no idle robot, then the order will not be assigned. This is acceptable for now, but we can solve this in the tick function.

