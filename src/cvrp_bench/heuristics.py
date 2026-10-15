from cvrp_bench.instance import Instance
from cvrp_bench.solution import Routes, route_load


def nearest_neighbor(inst: Instance) -> Routes:
    d, q, Q=inst.dist, inst.demand, inst.capacity
    unvisited = set(inst.customers)
    routes = []
    while unvisited:
        route, load, cur = [], 0, 0
        while True:
            fits = [c for c in unvisited if load + q[c] <= Q]
            if not fits:
                break
            nxt = min(fits, key=lambda c: d[cur][c])
            route.append(nxt)
            load += q[nxt]
            unvisited.remove(nxt)
            cur = nxt
        routes.append(route)
    return routes


def clarke_wright(inst: Instance) -> Routes:
    d, q, Q = inst.dist, inst.demand, inst.capacity
    route_of = {c: [c] for c in inst.customers}
    load = {id(r): q[r[0]] for r in route_of.values()}

    savings = sorted(
        ((d[0][i] + d[0][j] - d[i][j], i, j) for i in inst.customers for j in inst.customers if i < j),
        reverse=True,
    )
    for s, i, j in savings:
        if s <= 0:
            break
        ri, rj = route_of[i], route_of[j]
        if ri is rj or load[id(ri)] + load[id(rj)] > Q:
            continue
        if ri[-1] == i and rj[0] == j:
            merged = ri + rj
        elif ri[0] == i and rj[-1] == j:
            merged = rj + ri
        elif ri[0] == i and rj[0] == j:
            merged = ri[::-1] + rj
        elif ri[-1] == i and rj[-1] == j:
            merged = ri + rj[::-1]
        else:
            continue
        load[id(merged)] = load.pop(id(ri)) + load.pop(id(rj))
        for c in merged:
            route_of[c] = merged

    unique = {id(r): r for r in route_of.values()}
    return list(unique.values())


def two_opt(inst: Instance, route: list[int]) -> list[int]:
    d = inst.dist
    r = [0] + route + [0]
    improved = True
    while improved:
        improved = False
        for i in range(1, len(r) - 2):
            for j in range(i + 1, len(r) - 1):
                a, b, c, e = r[i - 1], r[i], r[j], r[j + 1]
                if d[a][c] + d[b][e] < d[a][b] + d[c][e]:
                    r[i:j + 1] = reversed(r[i:j + 1])
                    improved = True
    return r[1:-1]


def _best_relocate(inst: Instance, routes: Routes):
    d, q, Q = inst.dist, inst.demand, inst.capacity
    loads = [route_load(inst, r) for r in routes]
    best = (0, None)
    for a, ra in enumerate(routes):
        for i, c in enumerate(ra):
            prev = ra[i - 1] if i > 0 else 0
            nxt = ra[i + 1] if i + 1 < len(ra) else 0
            remove_gain = d[prev][c] + d[c][nxt] - d[prev][nxt]
            for b, rb in enumerate(routes):
                if b != a and loads[b] + q[c] > Q:
                    continue
                for pos in range(len(rb) + 1):
                    if b == a and pos in (i, i + 1):
                        continue
                    p = rb[pos - 1] if pos > 0 else 0
                    n = rb[pos] if pos < len(rb) else 0
                    if b == a and (p == c or n == c):
                        continue
                    insert_cost = d[p][c] + d[c][n] - d[p][n]
                    gain = remove_gain - insert_cost
                    if gain > best[0]:
                        best = (gain, (a, i, b, pos))
    return best


def _apply_relocate(routes: Routes, move) -> Routes:
    a, i, b, pos = move
    routes = [r[:] for r in routes]
    c = routes[a].pop(i)
    if a == b and pos > i:
        pos -= 1
    routes[b].insert(pos, c)
    return [r for r in routes if r]


def _best_swap(inst: Instance, routes: Routes):
    d, q, Q = inst.dist, inst.demand, inst.capacity
    loads = [route_load(inst, r) for r in routes]

    def nbrs(r, i):
        return (r[i - 1] if i > 0 else 0), (r[i + 1] if i + 1 < len(r) else 0)

    best = (0, None)
    for a in range(len(routes)):
        for b in range(a + 1, len(routes)):
            ra, rb = routes[a], routes[b]
            for i, x in enumerate(ra):
                pa, na = nbrs(ra, i)
                for j, y in enumerate(rb):
                    if loads[a] - q[x] + q[y] > Q or loads[b] - q[y] + q[x] > Q:
                        continue
                    pb, nb = nbrs(rb, j)
                    gain = (d[pa][x] + d[x][na] + d[pb][y] + d[y][nb]
                            - d[pa][y] - d[y][na] - d[pb][x] - d[x][nb])
                    if gain > best[0]:
                        best = (gain, (a, i, b, j))
    return best


def local_search(inst: Instance, routes: Routes) -> Routes:
    routes = [two_opt(inst, r) for r in routes if r]
    while True:
        g1, m1 = _best_relocate(inst, routes)
        g2, m2 = _best_swap(inst, routes)
        if g1 <= 0 and g2 <= 0:
            return routes
        if g1 >= g2:
            routes = _apply_relocate(routes, m1)
        else:
            a, i, b, j = m2
            routes = [r[:] for r in routes]
            routes[a][i], routes[b][j] = routes[b][j], routes[a][i]
        routes = [two_opt(inst, r) for r in routes]
