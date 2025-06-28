
from heapq import heappop, heappush


def get_weight(x, y, direction, weight_map):
    key = f"{x}.{y}"
    if key in weight_map:
        w = weight_map[key][direction]

        if w == -1: return None
        return w

    return 1

def neighbors(cell, weight_map, cells):
    x, y = cell
    dirs = [(-1, 0), (0, -1), (1, 0), (0, 1)]  # left, up, right, down
    for i, (dx, dy) in enumerate(dirs):
        nx, ny = x + dx, y + dy
        if [nx, ny] in cells:
            # direction_from = (i + 2) % 4: 0<->2, 1<->3
            direction_from = (i + 2) % 4
            w = get_weight(nx, ny, direction_from, weight_map)

            if w is not None: yield (nx, ny), w

def find_fastest_path(start, goal, weight_map, cells):
    open_set = []
    heappush(open_set, (0, tuple(start), [start]))
    visited = {}

    while open_set:
        cost, current, path = heappop(open_set)
        if list(current) == goal:
            return path

        if current in visited and visited[current] <= cost:
            continue

        visited[current] = cost
        for (nx, ny), w in neighbors(current, weight_map, cells):
            next_cell = (nx, ny)
            if next_cell not in visited or cost + w < visited[next_cell]:
                heappush(open_set, (cost + w, next_cell, path + [[nx, ny]]))

    return None