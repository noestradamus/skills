from pathlib import Path
import pytest
from neuroevolution_lab.config import ExperimentSpec
from neuroevolution_lab.runtime import execute,replay_run
from neuroevolution_lab.reporting import report

@pytest.mark.parametrize("method",["ga","map_elites","hyperneat"])
def test_report_has_measured_artifacts_and_executed_replay(tmp_path,method):
    s=ExperimentSpec(name="report evidence",method=method,target="navigation",population_size=4,generations=1,parameters={"horizon":8})
    assert execute(s,tmp_path)["status"]=="completed"
    replay_run(tmp_path,10000)
    output=report(tmp_path)
    assert output["resources"]["observed"]==4
    text=Path(output["report"]).read_text()
    assert "replay-10000.json" in text
    assert (tmp_path/"network.svg").exists() and (tmp_path/"learning-curve.svg").exists()
    if method=="map_elites": assert (tmp_path/"archive.json").exists()

def test_local_cartpole_agrees_with_gymnasium_constant_controller():
    import gymnasium as gym
    from neuroevolution_lab.search import evaluate_policy
    for seed in range(5):
        env=gym.make("CartPole-v1"); env.reset(seed=seed)
        count=0
        while True:
            _,_,terminated,truncated,_=env.step(1); count+=1
            if terminated or truncated: break
        env.close()
        result=evaluate_policy(lambda x:[1.],"cartpole",seed,{"episodes":1,"horizon":500})
        assert result["fitness"]==count
