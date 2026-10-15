import itertools
from pathlib import Path

import pytest

from cvrp_bench.exact import solve_mip
from cvrp_bench.heuristics import clarke_wright,nearest_neighbor,local_search,two_opt
from cvrp_bench.instance import Instance,euc_2d,read_sol,read_vrp
from cvrp_bench.metaheuristic import lns
from cvrp_bench.ortools_routing import solve_routing
from cvrp_bench.solution import route_cost,total_cost,validate

from cvrp_bench.cpp_solver import solve_cpp

DATA=Path(__file__).parent.parent/"data"

def tiny()->Instance:
    pts=[(0,0),(0,10),(10,10),(10,0),(5,12)]
    dem=[0,4,4,4,4]
    dist=[[euc_2d(p,q) for q in pts]for p in pts]
    return Instance("tiny",10,pts,dem,dist)

def brute_force(inst:Instance)->int|None:
    best=None
    cust=list(inst.customers)
    for perm in itertools.permutations(cust):
        for cuts in itertools.product([0,1],repeat=len(cust)-1):
            routes,cur=[],[perm[0]]
            for c,cut in zip(perm[1:],cuts):
                if cut:
                    routes.append(cur)
                    cur=[]
                cur.append(c)
            routes.append(cur)
            if not validate(inst,routes):
                c=total_cost(inst,routes)
                best=c if best is None else min(best,c)
    return best

def test_euc_2d_rounds_to_nearest():
    assert euc_2d((0,0),(3,4))==5
    assert euc_2d((0,0),(1,1))==1
    assert euc_2d((0,0),(1,2))==2

def test_route_cost_by_hand():
    inst=tiny()
    assert route_cost(inst,[1,4])==10+5+13

def test_validate_catches_errors():
    inst=tiny()
    assert validate(inst,[[1,2],[3,4]])==[]
    assert any("twice" in e for e in validate(inst,[[1,2],[2,3,4]]))
    assert any("capacity" in e for e in validate(inst,[[1,2,3],[4]]))
    assert any("never visited" in e for e in validate(inst,[[1,2]]))

@pytest.mark.parametrize("name",["A-n32-k5","P-n16-k8"])
def test_parser_reproduces_known_optimum(name):
    inst=read_vrp(DATA/f"{name}.vrp")
    routes,cost=read_sol(DATA/f"{name}.sol")
    assert validate(inst,routes)==[]
    assert total_cost(inst,routes)==cost==inst.optimal

def test_two_opt_never_worse():
    inst=read_vrp(DATA/"A-n32-k5.vrp")
    route=list(range(1,8))
    assert route_cost(inst,two_opt(inst,route))<=route_cost(inst,route)
    assert sorted(two_opt(inst,route))==route

@pytest.mark.parametrize("name",["A-n32-k5","A-n53-k7"])
def test_heuristics_feasible_and_ordered(name):
    inst=read_vrp(DATA/f"{name}.vrp")
    nn,cw=nearest_neighbor(inst),clarke_wright(inst)
    ls=local_search(inst,cw)
    for r in (nn,cw,ls):
        assert validate(inst,r)==[]
        assert total_cost(inst,r)>=inst.optimal
    assert total_cost(inst,ls)<=total_cost(inst,cw)

def test_all_methods_hit_brute_force_on_tiny():
    inst=tiny()
    opt=brute_force(inst)
    routes,status,obj,_=solve_mip(inst,10)
    assert status=="OPTIMAL" and round(obj)==opt==total_cost(inst,routes)
    assert total_cost(inst,lns(inst,0.5))==opt
    assert total_cost(inst,solve_routing(inst,1))==opt

def test_mip_proves_optimum_on_small_instance():
    inst=read_vrp(DATA/"P-n16-k8.vrp")
    routes,status,obj,_=solve_mip(inst,30,"CP-SAT")
    assert validate(inst,routes)==[]
    assert status=="OPTIMAL" and round(obj)==inst.optimal==total_cost(inst,routes)

# C++ testing, run make first

def write_vrp(inst:Instance,path:Path)->Path:
    lines=[f"NAME : {inst.name}","TYPE : CVRP",f"DIMENSION : {inst.n}","EDGE_WEIGHT_TYPE : EUC_2D",f"CAPACITY : {inst.capacity}","NODE_COORD_SECTION"]
    lines+=[f" {k+1} {x:g} {y:g}" for k,(x,y) in enumerate(inst.coords)]
    lines+=["DEMAND_SECTION"]+[f"{k+1} {q}" for k,q in enumerate(inst.demand)]
    lines+=["DEPOT_SECTION"," 1 "," -1 ","EOF "]
    path.write_text('\n'.join(lines)+'\n')
    return path

@pytest.mark.parametrize("name",["A-n32-k5","A-n53-k7","P-n23-k8"])
def test_cpp_heuristics_match_python_exactly(name):
    inst=read_vrp(DATA/f"{name}.vrp")
    cw=clarke_wright(inst)
    expected={"nn":nearest_neighbor(inst),"cw":cw,"ls":local_search(inst,cw)}
    for method,routes in expected.items():
        got,info=solve_cpp(DATA/f"{name}.vrp",method)
        assert got==routes,method
        assert validate(inst,got)==[] and info["cost"]==total_cost(inst,got)

def test_cpp_known_costs_a32():
    costs={m:solve_cpp(DATA/"A-n32-k5.vrp",m)[1]["cost"] for m in ("nn","cw","ls")}
    assert costs=={"nn":1145,"cw":839,"ls":827}

def test_cpp_lns_hits_brute_force_on_tiny(tmp_path):
    inst=tiny()
    routes,info=solve_cpp(write_vrp(inst,tmp_path/"tiny.vrp"),"lns",0.5)
    assert validate(inst,routes)==[] and total_cost(inst,routes)==brute_force(inst)
    assert info["iterations"]>0

def test_cpp_lns_near_optimal_and_valid():
    inst=read_vrp(DATA/"A-n32-k5.vrp")
    routes,info=solve_cpp(DATA/"A-n32-k5.vrp","lns",2)
    assert validate(inst,routes)==[]
    assert inst.optimal is not None
    assert total_cost(inst,routes)<=1.01*inst.optimal