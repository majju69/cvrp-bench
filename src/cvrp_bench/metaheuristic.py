import math
import random
import time

from cvrp_bench.heuristics import clarke_wright, local_search
from cvrp_bench.instance import Instance
from cvrp_bench.solution import Routes, route_load, total_cost

def ruin(inst: Instance, routes: Routes, k: int, rng: random.Random) -> tuple[Routes, list[int]]:
    seed = rng.choice(list(inst.customers))
    near = sorted(inst.customers, key=lambda c: inst.dist[seed][c])[:k]
    removed = set(near)
    kept = [[c for c in r if c not in removed] for r in routes]
    return [r for r in kept if r], near


def recreate(inst: Instance, routes: Routes, removed: list[int], rng: random.Random) -> Routes:
    d, q, Q = inst.dist, inst.demand, inst.capacity
    routes = [r[:] for r in routes]
    loads = [route_load(inst, r) for r in routes]
    rng.shuffle(removed)
    for c in removed:
        best = None
        for k, r in enumerate(routes):
            if loads[k] + q[c] > Q:
                continue
            for pos in range(len(r) + 1):
                p = r[pos - 1] if pos > 0 else 0
                n = r[pos] if pos < len(r) else 0
                delta = d[p][c] + d[c][n] - d[p][n]
                if best is None or delta < best[0]:
                    best = (delta, k, pos)
        if best is None:
            routes.append([c])
            loads.append(q[c])
        else:
            _, k, pos = best
            routes[k].insert(pos, c)
            loads[k] += q[c]
    return routes


def lns(inst: Instance, time_limit: float = 10.0, seed: int = 0, stats: dict | None = None) -> Routes:
    rng = random.Random(seed)
    iters = 0
    cur = local_search(inst, clarke_wright(inst))
    cur_cost = total_cost(inst, cur)
    best, best_cost = cur, cur_cost
    temp0 = 0.3 * cur_cost / inst.n
    start = time.perf_counter()
    while (elapsed := time.perf_counter() - start) < time_limit:
        temp = temp0 * (1 - elapsed / time_limit) + 1e-9
        k = rng.randint(3, max(4, inst.n // 6))
        partial, removed = ruin(inst, cur, k, rng)
        cand = local_search(inst, recreate(inst, partial, removed, rng))
        cand_cost = total_cost(inst, cand)
        if cand_cost < cur_cost or rng.random() < math.exp((cur_cost - cand_cost) / temp):
            cur, cur_cost = cand, cand_cost
            if cur_cost < best_cost:
                best, best_cost = cur, cur_cost
        iters += 1
    if stats is not None:
        stats["iterations"] = iters
    return best
