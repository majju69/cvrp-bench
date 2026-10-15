import argparse
import time
from collections.abc import Callable
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from cvrp_bench.cpp_solver import solve_cpp
from cvrp_bench.exact import solve_mip
from cvrp_bench.instance import read_vrp
from cvrp_bench.metaheuristic import lns
from cvrp_bench.ortools_routing import solve_routing
from cvrp_bench.solution import total_cost,validate

matplotlib.use("Agg")

def methods(path:Path,time_limit:float,compare_python_lns:bool):
    m={
        "nearest_neighbor":lambda inst:solve_cpp(path,"nn"),
        "clarke_wright":lambda inst:solve_cpp(path,"cw"),
        "cw+local_search":lambda inst:solve_cpp(path,"ls"),
        "lns":lambda inst:solve_cpp(path,"lns",time_limit),
        "ortools_gls":lambda inst:(solve_routing(inst,int(time_limit)),{}),
    }
    if compare_python_lns:
        def py_lns(inst):
            stats={}
            return lns(inst,time_limit,stats=stats),stats
        m["lns_python"]=py_lns
    return m


def run(data_dir:Path,out_dir:Path,time_limit:float,mip_limit:float,mip_max_n:int,compare_python_lns:bool=False)->pd.DataFrame:
    rows=[]
    for path in sorted(data_dir.glob("*.vrp"),key=lambda p:(read_vrp(p).n,p.name)):
        inst=read_vrp(path)
        runs:dict[str,Callable]=dict(methods(path,time_limit,compare_python_lns))
        if inst.n<=mip_max_n:
            runs["mip_scip"]=lambda i:(solve_mip(i,mip_limit,"SCIP"),{})
            runs["mip_cpsat"]=lambda i:(solve_mip(i,mip_limit,"CP-SAT"),{})
        for name,fn in runs.items():
            start=time.perf_counter()
            out,info=fn(inst)
            secs=time.perf_counter()-start
            status,bound="",None
            if name.startswith("mip"):
                out,status,_,bound=out
            routes=out or []
            errors=validate(inst,routes)
            cost=total_cost(inst,routes)
            rows.append({
                "instance":inst.name,"n":inst.n-1,"method":name,"cost":cost,
                "optimal":inst.optimal,"gap_pct":round(100*(cost-inst.optimal)/inst.optimal,2),
                "seconds":round(secs,2),"routes":len(routes),"feasible":not errors,
                "mip_status":status,"mip_bound":bound,"iterations":info.get("iterations"),
            })
            print(f"{inst.name:10} {name:17} cost={cost:5} gap={rows[-1]['gap_pct']:5.1f}% {secs:6.1f}s {'ok' if not errors else errors[0]}")

    df=pd.DataFrame(rows)
    out_dir.mkdir(exist_ok=True)
    df.to_csv(out_dir/"results.csv",index=False)

    table=df.pivot(index="instance",columns="method",values="gap_pct")
    table=table.loc[df.drop_duplicates("instance").instance]
    (out_dir/"summary.md").write_text(
        "Gap to optimal (%) per instance and method\n\n"+table.to_markdown()+"\n\n"
        "Mean gap (%)\n\n"+df.groupby("method").gap_pct.mean().round(2).to_markdown()+'\n'
    )

    if "lns_python" in set(df.method):
        sp=df[df.method.isin(["lns","lns_python"])].pivot(index="instance",columns="method",values=["iterations","gap_pct"])
        sp=sp.loc[df.drop_duplicates("instance").instance]
        sp[("speedup","x")]=(sp[("iterations","lns")]/sp[("iterations","lns_python")]).round(1)
        sp.columns=[f"{a}_{b}" for a,b in sp.columns]
        with open(out_dir/"summary.md","a") as f:
            f.write("\nC++ LNS vs Python LNS (same time limit)\n\n"+sp.to_markdown()+'\n')

    ax=table.drop(columns=["nearest_neighbor"]).plot(kind="bar",figsize=(11, 5))
    ax.set_ylabel("gap to optimal (%)")
    ax.set_title("CVRP: heuristics vs exact vs OR-Tools (lower is better)")
    plt.tight_layout()
    plt.savefig(out_dir/"gaps.png", dpi=120)
    return df


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data",default="data")
    p.add_argument("--out",default="results")
    p.add_argument("--time-limit",type=float,default=10,help="seconds for LNS and OR-Tools")
    p.add_argument("--mip-limit",type=float,default=60,help="seconds for the exact MIP")
    p.add_argument("--mip-max-n",type=int,default=25,help="only run the MIP up to this many nodes")
    p.add_argument("--compare-python-lns",action="store_true",help="also run the pure-Python LNS (speed comparison)")
    a=p.parse_args()
    run(Path(a.data),Path(a.out),a.time_limit,a.mip_limit,a.mip_max_n,a.compare_python_lns)

if __name__ == "__main__":
    main()