import json
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from neuroevolution_lab.config import ExperimentSpec
from neuroevolution_lab.runtime import Context,BudgetExceeded
from neuroevolution_lab.providers import complete

def test_openai_compatible_local_http_exchange_and_cache(tmp_path):
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            received.append((self.path,json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
            self.wfile.write(json.dumps({"model":"protocol-fixture", "choices":[{"message":{"content":"fixture response"}}],"usage":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5}}).encode())
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        s=ExperimentSpec(method="fixed_agent",target="arithmetic_tools",model={"provider":"endpoint","base_url":f"http://127.0.0.1:{server.server_port}/v1"},budget={"max_model_calls":1})
        ctx=Context(tmp_path,s); msg=[{"role":"user","content":"protocol test"}]
        assert complete(ctx,msg,"one")=="fixture response"
        assert complete(ctx,msg,"one")=="fixture response"
        assert len(received)==1 and received[0][0]=="/v1/chat/completions"
        with pytest.raises(BudgetExceeded): complete(ctx,msg,"two")
    finally:
        server.shutdown(); server.server_close(); thread.join()

def test_uncertain_endpoint_outcome_is_not_retried(tmp_path,monkeypatch):
    import neuroevolution_lab.providers as providers
    s=ExperimentSpec(method="fixed_agent",target="arithmetic_tools",model={"provider":"endpoint"})
    ctx=Context(tmp_path,s)
    def fail(*args,**kwargs): raise RuntimeError("connection lost")
    monkeypatch.setattr(providers.httpx,"post",fail)
    with pytest.raises(RuntimeError,match="connection lost"): complete(ctx,[],"key")
    with pytest.raises(RuntimeError,match="outcome unknown"): complete(ctx,[],"key")
