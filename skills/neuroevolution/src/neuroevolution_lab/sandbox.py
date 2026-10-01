"""No-network OCI execution for evolved Python programs."""
import ast
import json
import subprocess
import uuid
import os
import selectors
import time

DEFAULT_IMAGE="python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f"

def check_program(code):
    if len(code)>16000: raise ValueError("Candidate program exceeds 16,000 characters")
    tree = ast.parse(code)
    if not any(isinstance(n,ast.FunctionDef) and n.name=="solve" for n in tree.body):
        raise ValueError("Program requires solve(a,b,c,d)")
    if any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(tree)):
        raise ValueError("This arithmetic-program profile does not allow imports")

def run_program(code, cases, image=DEFAULT_IMAGE, timeout=15):
    check_program(code)
    identity = subprocess.run(["docker","image","inspect",image,"--format","{{.Id}}"],capture_output=True,text=True,timeout=10)
    if identity.returncode: raise RuntimeError(f"Sandbox image missing: explicitly pull {image} before this profile")
    name = "neuroevo-"+uuid.uuid4().hex
    wrapper = "import json,sys\np=json.load(sys.stdin)\nn={}\nexec(compile(p['code'],'candidate','exec'),n)\nprint(json.dumps([n['solve'](*c) for c in p['cases']]))"
    resolved_image=identity.stdout.strip()
    command = ["docker","run","--rm","-i","--name",name,"--network","none","--read-only","--cap-drop","ALL",
        "--security-opt","no-new-privileges","--user","65534:65534","--memory","256m","--cpus","1","--pids-limit","32",
        "--tmpfs","/tmp:rw,noexec,nosuid,size=16m",resolved_image,"python","-I","-c",wrapper]
    process=None
    try:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        process.stdin.write(json.dumps({"code":code,"cases":cases}).encode()); process.stdin.close()
        chunks=[]; total=0; deadline=time.monotonic()+timeout
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout,selectors.EVENT_READ)
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0: raise subprocess.TimeoutExpired(command,timeout)
                events=selector.select(min(remaining,.2))
                if events:
                    data=os.read(process.stdout.fileno(),65536)
                    if not data: break
                    total+=len(data)
                    if total>262144: raise ValueError("Candidate output exceeds 256 KiB")
                    chunks.append(data)
        output_text=b"".join(chunks).decode("utf8",errors="replace")
        returncode=process.wait(timeout=max(.1,deadline-time.monotonic()))
        if returncode: raise ValueError("Candidate program failed: "+output_text[-1000:])
        output = json.loads(output_text)
        if not isinstance(output,list) or len(output)!=len(cases): raise ValueError("Invalid candidate result shape")
        return output,identity.stdout.strip()
    finally:
        if process is not None and process.poll() is None:
            process.kill(); process.wait(timeout=5)
        subprocess.run(["docker","rm","-f",name],capture_output=True,timeout=10)
