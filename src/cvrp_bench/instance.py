import math
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Instance:
    name: str
    capacity: int
    coords: list[tuple[float, float]]
    demand: list[int]
    dist: list[list[int]]
    optimal: int|None=None

    @property
    def n(self)->int:
        return len(self.coords)

    @property
    def customers(self)->range:
        return range(1,self.n)

def euc_2d(a:tuple[float,float],b:tuple[float,float])->int:
    return int(math.sqrt((a[0]-b[0])**2+(a[1]-b[1])**2)+0.5)

def read_vrp(path:str|Path)->Instance:
    lines=Path(path).read_text().splitlines()
    header:dict[str,str]={}
    coords:dict[int,tuple[float,float]]={}
    demand:dict[int,int]={}
    depot=1
    section=None
    for raw_line in lines:
        line=raw_line.strip()
        if not line or line=="EOF":
            continue
        if line.endswith("_SECTION"):
            section=line
            continue
        if ":" in line and section is None:
            key,val=line.split(":",1)
            header[key.strip()]=val.strip()
            continue
        parts=line.split()
        if section=="NODE_COORD_SECTION":
            coords[int(parts[0])]=(float(parts[1]),float(parts[2]))
        elif section=="DEMAND_SECTION":
            demand[int(parts[0])]=int(parts[1])
        elif section=="DEPOT_SECTION":
            if int(parts[0])!=-1:
                depot=int(parts[0])

    if header.get("EDGE_WEIGHT_TYPE")!="EUC_2D":
        raise ValueError(f"only EUC_2D instances are supported, got {header.get('EDGE_WEIGHT_TYPE')}")

    if depot!=1:
        raise ValueError("expected the depot to be node 1")

    ids=sorted(coords)
    pts=[coords[i] for i in ids]
    dem=[demand[i] for i in ids]
    dist=[[euc_2d(i,j) for j in pts] for i in pts]

    optimal=None
    comment=header.get("COMMENT","")
    if "value:"in comment:
        optimal=int(comment.split("value:")[1].strip(')'))

    return  Instance(header["NAME"],int(header["CAPACITY"]),pts,dem,dist,optimal)

def read_sol(path:str|Path)->tuple[list[list[int]],int|None]:
    routes,cost=[],None
    for line in Path(path).read_text().splitlines():
        if line.startswith("Route"):
            routes.append([int(x) for x in line.split(":")[1].split()])
        elif line.startswith("Cost"):
            cost=int(float(line.split()[1]))
    return routes,cost