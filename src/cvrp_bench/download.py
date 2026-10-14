import urllib.request
from pathlib import Path

BASE="https://galgos.inf.puc-rio.br/cvrplib/index.php/en/download"

INSTANCES={
"P-n16-k8": 75,
"P-n19-k2": 76,
"P-n20-k2": 77,
"P-n21-k2": 78,
"P-n22-k2": 79,
"P-n23-k8": 81,
"A-n32-k5": 4,
"A-n33-k5": 5,
"A-n37-k6": 11,
"A-n39-k5": 13,
"A-n45-k7": 17,
"A-n53-k7": 20,
"A-n62-k8": 25,
"A-n69-k9": 30,
"A-n80-k10": 31,
}

def main(out_dir:str="data")->None:
    out=Path(out_dir)
    out.mkdir(exist_ok=True)
    for name,iid in INSTANCES.items():
        vrp=out/f"{name}.vrp"
        if not vrp.exists():
            urllib.request.urlretrieve(f"{BASE}/instance/{iid}",vrp)
        sol=out/f"{name}.sol"
        if not sol.exists():
            urllib.request.urlretrieve(f"{BASE}/bks/{iid}",sol)
        print("ok",name)

if __name__=="__main__":
    main()