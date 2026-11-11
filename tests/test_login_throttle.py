from fastapi.testclient import TestClient
from test_partners import app, setup


def test_shared_login_attempt_budget_across_workers():
    from concurrent.futures import ThreadPoolExecutor
    from app.core import login_limit_key,login_attempt_allowed,clear_login_failures
    with TestClient(app) as staff:
        setup(staff)
        key=login_limit_key('concurrent-ip','multi@sample.local');clear_login_failures(key)
        with ThreadPoolExecutor(max_workers=8) as pool:allowed=list(pool.map(lambda _:login_attempt_allowed(key),range(12)))
        assert sum(allowed)==5
        assert not login_attempt_allowed(key)
        import subprocess, os, sys
        from app.core import engine, DATA_DIR
        env={**os.environ,'DATABASE_URL':str(engine.url),'FRAMATEX_DATA_DIR':str(DATA_DIR)}
        subprocess.run([sys.executable,'-c',"from app.main import app; from app.core import login_limit_key,login_attempt_allowed; assert not login_attempt_allowed(login_limit_key('concurrent-ip','multi@sample.local'))"],env=env,check=True)
        clear_login_failures(key);assert login_attempt_allowed(key)
