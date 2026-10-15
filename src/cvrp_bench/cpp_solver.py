import subprocess
from pathlib import Path

BINARY=Path(__file__).resolve().parents[2]/"build"/"cvrp_solve"

def solve_cpp(vrp_path:str|Path,method:str,seconds:float=10.0,seed:int=0)->tuple[list[list[int]],dict]:
    if not BINARY.exists():
        raise FileNotFoundError(f"{BINARY} not found: run make first")
    out=subprocess.run([str(BINARY),str(vrp_path),method,str(seconds),str(seed)],capture_output=True,text=True,check=True,timeout=seconds+60).stdout
    routes,info=[],{}
    for line in out.splitlines():
        key,*rest=line.split()
        if key=="route":
            routes.append([int(x) for x in rest])
        else:
            info[key]=float(rest[0])
    return routes,info