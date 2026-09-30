"""Actual model-mediated agent search with externally checked arithmetic tools.

The bounded task is intentionally small. Scores are measured task success, not
LLM judgments. This is program/agent evolution, not neural-weight evolution;
neural_router additionally evolves a real neural gate around the fixed model.
"""
from copy import deepcopy
import ast
import hashlib
import json
import operator
import numpy as np
from .providers import complete
from .sandbox import run_program,check_program,DEFAULT_IMAGE
from .runtime import encoded

OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul}
def calculate(expression):
    if len(expression)>120: raise ValueError("Expression too long")
    def visit(node,depth=0):
        if depth>12: raise ValueError("Expression too deep")
        if isinstance(node,ast.Constant) and type(node.value) is int and abs(node.value)<1000000: return node.value
        if isinstance(node,ast.BinOp) and type(node.op) in OPS:
            val=OPS[type(node.op)](visit(node.left,depth+1),visit(node.right,depth+1))
            if abs(val)>10**12: raise ValueError("Arithmetic result outside profile bounds")
            return val
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub): return -visit(node.operand,depth+1)
        raise ValueError("Only bounded integer addition, subtraction, multiplication are allowed")
    try:
        tree=ast.parse(expression,mode="eval")
    except SyntaxError as error:
        raise ValueError("Invalid arithmetic expression syntax") from error
    return visit(tree.body)

def model_json(text):
    # JSON is the protocol. No executable parsing and no implicit repair.
    value=json.loads(text)
    if not isinstance(value,dict): raise ValueError("Model must return a JSON object")
    return value

def validate_genome(genome,program=False):
    if program:
        if set(genome)!={"kind","code"} or genome["kind"]!="program" or not isinstance(genome["code"],str): raise ValueError("Expected program genome")
        check_program(genome["code"])
    else:
        if set(genome)-{"kind","prompt","nodes","router"}: raise ValueError("Unknown genome fields")
        if genome.get("kind")!="agent" or not isinstance(genome.get("prompt"),str) or len(genome["prompt"])>6000: raise ValueError("Invalid prompt genome")
        if not isinstance(genome.get("nodes"),list) or not 1<=len(genome["nodes"])<=6: raise ValueError("Workflow needs 1-6 typed nodes")
        if genome["nodes"][0]!="model" or any(x not in ("model","calculate","verify") for x in genome["nodes"]): raise ValueError("Workflow must start with model and use allowlisted primitives")
        if genome["nodes"].count("model")!=1: raise ValueError("This bounded workflow profile allows one model node")
        if "router" in genome:
            router=genome["router"]
            if not isinstance(router,list) or len(router)!=3 or not all(type(x) in (int,float) for x in router):
                raise ValueError("Router requires three finite neural weights in a list")
            try:
                finite=bool(np.isfinite(np.asarray(router,dtype=float)).all())
            except (TypeError,ValueError,OverflowError):
                finite=False
            if not finite: raise ValueError("Router requires three finite neural weights in a list")
    return genome

def cases(seed,n):
    r=np.random.default_rng(seed)
    return r.integers(2,40,size=(n,4)).tolist()

def task_message(case):
    a,b,c,d=case
    return f"Compute ({a} + {b}) * {c} - {d}. Return JSON with either answer (an integer), or tool='calculate' and expression (a literal arithmetic expression)."

class AgentEngine:
    def __init__(self,spec):
        self.spec=spec; self.method=spec["method"]
        if spec["target"]!="arithmetic_tools": raise ValueError("LLM profiles currently support target arithmetic_tools")
        if spec["model"]["provider"]=="disabled": raise ValueError("LLM method requires model.provider bridge or endpoint")
        self.rng=np.random.default_rng(spec["seed"]); self.generation=0; self.done=False
        program=spec["parameters"].get("program",False)
        if type(program) is not bool: raise ValueError("parameters.program must be a boolean")
        if program and self.method not in ("llm_program","llm_holdout"):
            raise ValueError("Program execution requires llm_program or llm_holdout")
        self.program=self.method=="llm_program" or program
        self.population=[]; self.archive={}; self.best=None; self.history=[]
        self.training=cases(spec["seed"]+71,int(spec["parameters"].get("train_cases",2)))
        self.parent_count=max(2,spec["population_size"]//2)
    def proposal(self,ctx,i):
        if self.method=="fixed_agent":
            return {"kind":"agent","prompt":"Solve the user task accurately. Return only the requested JSON.","nodes":["model","calculate"]}
        parents=[] if not self.population or self.method=="random_agent" else [self.population[i%len(self.population)]["genome"]]
        if self.method=="greedy_agent" and self.best:
            parents=[self.best["genome"]]
        if self.method=="llm_crossover" and self.population:
            parents.append(self.population[(i+1)%len(self.population)]["genome"])
        schema='{"kind":"program","code":"def solve(a,b,c,d): ..."}' if self.program else '{"kind":"agent","prompt":"instructions for the solver","nodes":["model","calculate","verify"]}'
        instruction=("Produce one executable candidate genome as JSON only. Task family: integer arithmetic (a+b)*c-d. "
            "No answers for evaluation cases are available. Propose a meaningfully distinct strategy. "
            +("Use compatible strengths from BOTH parents. " if len(parents)>1 else "Mutate the parent if supplied; preserve useful behavior. ")+"Schema: "+schema)
        msg=[{"role":"system","content":instruction},{"role":"user","content":encoded({"generation":self.generation,"candidate":i,"parents":parents,"observed_history":[] if self.method=="random_agent" else self.history[-2:]})}]
        genome=validate_genome(model_json(complete(ctx,msg,f"proposal-{self.generation}-{i}")),self.program)
        if self.method=="llm_prompt":
            if "router" in genome:
                raise ValueError("llm_prompt evolves prompts only; a neural router requires neural_router")
            genome["nodes"]=["model","calculate","verify"]
        if self.method=="neural_router":
            old=parents[0].get("router") if parents else None
            genome["router"]=(np.asarray(old)+self.rng.normal(0,.25,3) if old is not None else self.rng.normal(0,1,3)).tolist()
        ctx.record({"event":"variation","method":self.method,"generation":self.generation,"candidate":i,"parents":[hashlib.sha256(encoded(p).encode()).hexdigest() for p in parents],"genome":genome})
        return genome
    def evaluate_agent(self,ctx,genome,index,evaluation_cases):
        successes=0; tools=0; verified=0; outputs=[]
        if self.program:
            answers,image=run_program(genome["code"],evaluation_cases,image=self.spec["parameters"].get("docker_image",DEFAULT_IMAGE))
            for c,answer in zip(evaluation_cases,answers):
                expected=(c[0]+c[1])*c[2]-c[3]
                successes+=type(answer) is int and answer==expected
            return {"fitness":successes/len(evaluation_cases),"descriptor":[min(len(genome["code"])/500,1),0],"metrics":{"answers":answers,"image":image,"cases":len(evaluation_cases)}}
        msg=[{"role":"system","content":genome["prompt"]},
             {"role":"user","content":"Solve each independent task. Return JSON {\"actions\": [one action object per task in order]}. Tasks:\n"+"\n".join(task_message(c) for c in evaluation_cases)}]
        raw=complete(ctx,msg,f"solve-{self.generation}-{index}")
        try:
            actions=model_json(raw)["actions"]
            if not isinstance(actions,list) or len(actions)!=len(evaluation_cases): raise ValueError("Wrong action count")
        except (ValueError,KeyError,TypeError) as e:
            return {"fitness":0.,"descriptor":[0.,0.],"constraints":False,"metrics":{"protocol_error":str(e),"cases":len(evaluation_cases),"model_calls":1}}
        for j,c in enumerate(evaluation_cases):
            try:
                action=actions[j]
                if not isinstance(action,dict) or set(action)-{"answer","tool","expression"}: raise ValueError("Invalid action fields")
                answer=action.get("answer"); used_tool=False
                use_calc="calculate" in genome["nodes"]
                if "router" in genome:
                    x=np.array([1,sum(c)/160,float(action.get("tool")=="calculate")])
                    use_calc=use_calc and float(np.dot(genome["router"],x))>=0
                used_verify=False
                for node in genome["nodes"][1:]:
                    if node=="calculate" and use_calc and action.get("tool")=="calculate":
                        answer=calculate(action["expression"]); used_tool=True
                    elif node=="verify":
                        # Reject, without replacing the answer or consulting evaluator data.
                        expected_via_tool=calculate(f"({c[0]}+{c[1]})*{c[2]}-{c[3]}")
                        used_verify=True
                        if answer!=expected_via_tool: answer=None
                tools+=used_tool; verified+=used_verify
                expected=(c[0]+c[1])*c[2]-c[3]
                ok=type(answer) is int and answer==expected
                successes+=ok
                outputs.append({"answer":answer,"correct":ok,"tool_used":used_tool})
            except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:
                outputs.append({"error":str(e),"correct":False})
        n=len(evaluation_cases)
        return {"fitness":successes/n,"descriptor":[tools/n,verified/n],"metrics":{"outputs":outputs,"cases":n,"model_calls":1}}
    def step(self,ctx):
        evaluated=[]
        for i in range(self.spec["population_size"]):
            genome=self.proposal(ctx,i)
            result=ctx.evaluate(genome,lambda:self.evaluate_agent(ctx,genome,i,self.training),label=f"agent-g{self.generation}-c{i}")
            row={"genome":genome,"result":result}; evaluated.append(row)
            cell=tuple(min(int(x*3),2) for x in result["descriptor"])
            if cell not in self.archive or result["fitness"]>self.archive[cell]["result"]["fitness"]: self.archive[cell]=deepcopy(row)
            if self.best is None or result["fitness"]>self.best["result"]["fitness"]: self.best=deepcopy(row)
        # Archive occupants are active parents, preserving distinct executed behaviors.
        pool=list(self.archive.values())+sorted(evaluated,key=lambda r:r["result"]["fitness"],reverse=True)
        unique={}
        for row in pool: unique.setdefault(encoded(row["genome"]),row)
        # Distinct reproductive parents are essential for actual crossover at pop_size=2.
        self.parent_count=max(2,self.spec["population_size"]//2)
        best_key=encoded(self.best["genome"])
        alternatives=[row for key,row in unique.items() if key!=best_key]
        take=min(self.parent_count-1,len(alternatives))
        selected=self.rng.choice(len(alternatives),size=take,replace=False).tolist() if take else []
        self.population=[deepcopy(self.best)]+[alternatives[i] for i in selected]
        self.history.append({"generation":self.generation,"best":self.best["result"]["fitness"],"coverage":len(self.archive)})
        self.generation+=1; self.done=self.generation>=self.spec["generations"]
    def summary(self):
        return {"method":self.method,"generation":self.generation,"best":self.best,"history":self.history,"archive":[{"cell":list(k),**v} for k,v in self.archive.items()],"claim":"Measured arithmetic-tool agent behavior; base language-model weights unchanged"}
    def replay(self,seed=10000):
        if self.best is None: return {"status":"no_candidate"}
        if self.program:
            c=cases(seed,5); values,image=run_program(self.best["genome"]["code"],c,image=self.spec["parameters"].get("docker_image",DEFAULT_IMAGE))
            return {"fitness":sum(type(v) is int and v==(a+b)*z-d for v,(a,b,z,d) in zip(values,c))/len(c),"image":image,"seed":seed}
        return {"status":"requires_live_evaluation","genome":self.best["genome"],"seed":seed,"note":"Use evaluate-heldout for fresh model calls. Replaying stored text does not establish held-out performance."}

class HoldoutEngine(AgentEngine):
    """A frozen candidate measured on independently generated cases, never selected on them."""
    def __init__(self,spec):
        super().__init__(spec)
        genome=validate_genome(deepcopy(spec["parameters"]["genome"]),self.program)
        self.best={"genome":genome,"result":None}
        self.training=cases(spec["seed"],int(spec["parameters"].get("cases",8)))
    def step(self,ctx):
        g=self.best["genome"]
        result=ctx.evaluate(g,lambda:self.evaluate_agent(ctx,g,0,self.training),label="frozen-heldout")
        self.best["result"]=result; self.generation=1; self.done=True
        self.history=[{"generation":0,"best":result["fitness"]}]

METHODS={name:AgentEngine for name in ("llm_prompt","llm_workflow","llm_program","llm_mutation","llm_crossover","neural_router","fixed_agent","random_agent","greedy_agent")}
METHODS["llm_holdout"]=HoldoutEngine
