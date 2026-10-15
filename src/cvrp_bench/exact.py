from ortools.linear_solver import pywraplp
from cvrp_bench.instance import Instance
from cvrp_bench.solution import Routes

def solve_mip(inst:Instance,time_limit:float=60.0,solver_name:str="SCIP",truck_bound:bool=True):
    n,dis,dem,cap=inst.n,inst.dist,inst.demand,inst.capacity
    s=pywraplp.Solver.CreateSolver(solver_name)
    if s is None:
        raise  RuntimeError(f"Solver {solver_name} not available")
    x={(i,j):s.BoolVar(f"x_{i}_{j}") for i in range(n) for j in range(n) if i!=j}
    u={i:s.NumVar(dem[i],cap,f"u_{i}") for i in inst.customers}

    for i in inst.customers:
        s.Add(sum(x[i,j] for j in range(n) if j!=i)==1)
        s.Add(sum(x[j,i] for j in range(n) if j!=i)==1)
    s.Add(sum(x[0,j] for j in inst.customers)==sum(x[i,0] for i in inst.customers))
    if truck_bound:
        min_trucks=-(-sum(dem)//cap)
        s.Add(sum(x[0,j] for j in inst.customers)>=min_trucks)
    for i in inst.customers:
        for j in inst.customers:
            if i!=j:
                s.Add(u[j]>=u[i]+dem[j]-cap*(1-x[i,j]))
    s.Minimize(sum(dis[i][j] *x[i,j] for (i,j) in x))
    s.SetTimeLimit(int(time_limit*1000))
    status=s.Solve()
    names={pywraplp.Solver.OPTIMAL:"OPTIMAL",pywraplp.Solver.FEASIBLE:"FEASIBLE"}
    if status not in names:
        return None,"NO SOLUTION",None,None
    succ={i:j for (i,j),var in x.items() if var.solution_value()>0.5}
    routes:Routes=[]
    for j in inst.customers:
        if x[0,j].solution_value()>0.5:
            route,cur=[],j
            while cur!=0:
                route.append(cur)
                cur=succ[cur]
            routes.append(route)
    return routes,names[status],s.Objective().Value(),s.Objective().BestBound()