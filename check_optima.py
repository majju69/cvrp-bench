from pathlib import Path
from cvrp_bench.instance import read_sol,read_vrp
from cvrp_bench.solution import total_cost,validate

for vrp in sorted(Path("data").glob("*.vrp")):
    inst=read_vrp(vrp)
    routes,cost=read_sol(vrp.with_suffix(".sol"))
    errs=validate(inst,routes)
    mine=total_cost(inst,routes)
    ok=not errs and mine==cost==inst.optimal
    print(f"{inst.name:10} file={cost} mine={mine} opt={inst.optimal} {'OK' if ok else errs}")