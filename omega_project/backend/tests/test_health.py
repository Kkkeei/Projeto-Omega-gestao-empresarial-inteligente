from fastapi.testclient import TestClient
from backend.main import app

def test_health():
    assert TestClient(app).get('/health').status_code == 200


def test_startup_nao_sincroniza_automaticamente():
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app):
        assert app.state.sincronizacao_inicial is None
