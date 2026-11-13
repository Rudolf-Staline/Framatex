"""Routers and domain helpers must load independently of the application assembler."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_main_exports_are_not_dependencies_of_domain_modules():
    dependencies=[]
    for path in (ROOT/'app').glob('*.py'):
        if path.name=='main.py':continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.ImportFrom) and (node.module=='app.main' or node.module=='main' and node.level==1):
                # The demo exercises the HTTP application through TestClient.
                if path.name=='seed_phase2_demo.py' and all(n.name=='app' for n in node.names):continue
                dependencies.append(f'{path.name}:{node.lineno}')
            elif isinstance(node,ast.Import) and any(n.name=='app.main' for n in node.names):
                dependencies.append(f'{path.name}:{node.lineno}')
    assert not dependencies,dependencies


@pytest.mark.parametrize('reverse',[False,True])
def test_routers_import_before_app_in_fresh_interpreter(tmp_path,reverse):
    modules=sorted(('app.'+path.stem for path in (ROOT/'app').glob('*routes.py')),reverse=reverse)
    env={**os.environ,'FRAMATEX_DATA_DIR':str(tmp_path),'FRAMATEX_SECRET_KEY':'cold-router-test-secret-'*3,'FRAMATEX_GUIDE_AI_ENABLED':'0'}
    env.pop('DATABASE_URL',None)
    script='import importlib,sys\nfor module in '+repr(modules)+':\n importlib.import_module(module)\n assert "app.main" not in sys.modules,module\n'
    result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
