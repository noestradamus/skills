import os
import subprocess
import pytest
from neuroevolution_lab.sandbox import run_program,check_program

@pytest.mark.parametrize("code",["import os\ndef solve(a,b,c,d): return 0", "print(1)"])
def test_program_grammar(code):
    with pytest.raises(ValueError): check_program(code)

@pytest.mark.skipif(os.environ.get("NEUROEVO_DOCKER_TESTS")!="1",reason="Explicit Docker execution validation; enable NEUROEVO_DOCKER_TESTS=1")
def test_real_isolated_program_execution_and_limits():
    result,identity=run_program("def solve(a,b,c,d): return (a+b)*c-d",[[2,3,4,1]])
    assert result==[19] and identity.startswith("sha256:")
    # Imports through builtins bypass grammar deliberately: Docker must enforce isolation.
    code="def solve(a,b,c,d):\n return __import__('os').getuid()"
    assert run_program(code,[[0,0,0,0]])[0]==[65534]
    with pytest.raises(ValueError,match="failed"):
        run_program("def solve(a,b,c,d):\n open('/root/host-secret','w').write('no')\n return 1",[[0,0,0,0]])
    with pytest.raises(ValueError,match="failed"):
        run_program("def solve(a,b,c,d):\n return __import__('socket').create_connection(('1.1.1.1',80),1)",[[0,0,0,0]])
    with pytest.raises(subprocess.TimeoutExpired):
        run_program("def solve(a,b,c,d):\n while True: pass",[[0,0,0,0]],timeout=1)
    with pytest.raises(ValueError,match="output exceeds"):
        run_program("def solve(a,b,c,d):\n print('x'*300000)\n return 1",[[0,0,0,0]])
