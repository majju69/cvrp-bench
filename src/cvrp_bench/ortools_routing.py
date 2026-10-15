from ortools.constraint_solver import pywrapcp,routing_enums_pb2

from cvrp_bench.instance import Instance
from cvrp_bench.solution import Routes

def solve_routing(inst: Instance,time_limit:int=10,vehicles:int|None=None) -> Routes:
    vehicles=vehicles or inst.n-1
    manager=pywrapcp.RoutingIndexManager(inst.n,vehicles,0)
    routing=pywrapcp.RoutingModel(manager)

    def distance(from_index,to_index):
        return inst.dist[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit=routing.RegisterTransitCallback(distance)
    routing.SetArcCostEvaluatorOfAllVehicles(transit)

    def demand(from_index):
        return inst.demand[manager.IndexToNode(from_index)]

    demand_cb=routing.RegisterUnaryTransitCallback(demand)
    routing.AddDimensionWithVehicleCapacity(demand_cb,0,[inst.capacity]*vehicles,True,"Load")

    params=pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.SAVINGS
    params.local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds=time_limit

    sol=routing.SolveWithParameters(params)

    if sol is None:
        return []

    routes=[]
    for v in range(vehicles):
        idx,route=sol.Value(routing.NextVar(routing.Start(v))),[]
        while not routing.IsEnd(idx):
            route.append(manager.IndexToNode(idx))
            idx=sol.Value(routing.NextVar(idx))
        if route:
            routes.append(route)
    return routes