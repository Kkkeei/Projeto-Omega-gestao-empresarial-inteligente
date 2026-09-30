from fastapi.testclient import TestClient
from main import app


def auth_headers(client: TestClient):
    response = client.post('/api/v1/auth/login', json={'email': 'admin@omega.local', 'senha': 'Admin@123'})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_health():
    response = TestClient(app).get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_api_requires_login():
    response = TestClient(app).get('/api/v1/empresas')
    assert response.status_code == 401


def test_login_and_me():
    client = TestClient(app)
    response = client.post('/api/v1/auth/login', json={'email': 'admin@omega.local', 'senha': 'Admin@123'})
    assert response.status_code == 200
    token = response.json()['access_token']
    me = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me.status_code == 200
    assert me.json()['email'] == 'admin@omega.local'


def test_listar_empresas():
    client = TestClient(app)
    headers = auth_headers(client)
    response = client.get('/api/v1/empresas', headers=headers)
    assert response.status_code == 200
    assert 'empresas' in response.json()


def test_dashboard():
    client = TestClient(app)
    headers = auth_headers(client)
    response = client.get('/api/v1/dashboard/resumo', headers=headers)
    assert response.status_code == 200
    assert 'empresas' in response.json()
