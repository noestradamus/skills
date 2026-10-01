"""Rebuild static reports from preserved evidence without rerunning searches."""
from pathlib import Path
import argparse
import json
from neuroevolution_lab.reporting import report

def main():
    p=argparse.ArgumentParser(); p.add_argument("root",type=Path); args=p.parse_args()
    rows=[]
    for status in sorted(args.root.rglob("status.json")):
        path=status.parent
        if not (path/"manifest.json").exists(): continue
        state=json.loads(status.read_text())
        if state["status"]=="waiting_for_model": continue
        try: rows.append({"run":str(path),"result":report(path)})
        except Exception as e: rows.append({"run":str(path),"error":str(e)})
    (args.root/"report-generation.json").write_text(json.dumps(rows,indent=2)+"\n")
    print(json.dumps({"reports":len(rows),"errors":[r for r in rows if "error" in r]}))

if __name__=="__main__": main()
