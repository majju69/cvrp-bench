from cvrp_bench.instance import Instance

Routes=list[list[int]]

def route_cost(inst:Instance,route:list[int])->int:
    if not route:
        return 0
    d=inst.dist
    c=d[0][route[0]]+d[route[-1]][0]
    for a,b in zip(route,route[1:]):
        c+=d[a][b]
    return c

def total_cost(inst:Instance,route:Routes)->int:
    return sum(route_cost(inst,r) for r in route)

def route_load(inst:Instance,route:list[int])->int:
    return sum(inst.demand[r] for r in route)

def validate(inst:Instance,routes:Routes)->list[str]:
    errors=[]
    seen:dict[int,int]={}
    for k,r in enumerate(routes):
        for c in r:
            if not 1<=c<inst.n:
                errors.append(f"route {k}: node {c} is not a customer")
            elif c in seen:
                errors.append(f"customer {c} visited twice (routes {seen[c]} and {k}")
            else:
                seen[c]=k
        load=route_load(inst,[c for c in r if 1<=c<inst.n])
        if load>inst.capacity:
            errors.append(f"route {k}: load {load} > capacity {inst.capacity}")
    missing=[c for c in inst.customers if c not in seen]
    if missing:
        errors.append(f"customers never visited: {missing}")
    return errors