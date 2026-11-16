import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("TAYYAR_DB", str(db_file))
    monkeypatch.setenv("TAYYAR_UPLOADS", str(tmp_path / "uploads"))
    # Fresh import so DB_PATH / UPLOAD_DIR pick up the env vars.
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    import app.db as dbmod
    import app.main as mainmod
    dbmod.init_db()
    with TestClient(mainmod.app) as c:
        yield c


@pytest.fixture()
def shop(client):
    r = client.post("/api/shops", json={
        "name": "Test General Store", "owner_name": "Test Owner",
        "phone": "0300-1111111", "address": "F-6, Islamabad",
        "sector": "General Store", "ntn": "DEMO-NTN-9999",
    })
    assert r.status_code == 201, r.text
    return r.json()
