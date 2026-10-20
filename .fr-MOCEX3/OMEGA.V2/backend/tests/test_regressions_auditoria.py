from datetime import date, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from app.services.auth_service import create_access_token, criar_usuario
from app.modules.certificados.service import cadastrar_a3


def _token_for(email: str):
    with __import__('app.db.database', fromlist=['conectar_banco']).conectar_banco() as conn:
        row = conn.execute('SELECT * FROM usuarios WHERE email=?', (email,)).fetchone()
    assert row is not None
    return {'Authorization': f"Bearer {create_access_token(dict(row))}"}


def _login(client: TestClient, email: str, password: str):
    response = client.post('/api/v1/auth/login', json={'email': email, 'senha': password})
    assert response.status_code == 200, response.text
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_inativar_empresa_exige_admin():
    email = f"auditoria-user-{uuid4().hex}@omega.local"
    criar_usuario('Usuário Auditoria', email, 'User@12345', 'USUARIO')
    with TestClient(app) as client:
        user_headers = _token_for(email)
        forbidden = client.post(
            '/api/v1/empresas/1/inativar',
            headers=user_headers,
            json={'data_saida': '2026-10-08', 'observacao': 'teste'},
        )
        assert forbidden.status_code == 403

        admin_headers = _token_for('admin@omega.local')
        # A operação é exercitada em uma empresa de teste inserida diretamente
        # na base isolada da suíte para não depender da validação de CNPJ externo.
        from app.db.database import conectar_banco
        with conectar_banco() as conn:
            cur = conn.execute(
                "INSERT INTO empresas (cnpj, razao_social, ativo) VALUES (?, ?, 1)",
                ('11444777000188', 'EMPRESA AUDITORIA LTDA'),
            )
            empresa_id = int(cur.lastrowid)
            conn.commit()
        ok = client.post(
            f'/api/v1/empresas/{empresa_id}/inativar',
            headers=admin_headers,
            json={'data_saida': '2026-10-08', 'observacao': 'teste'},
        )
        assert ok.status_code == 200, ok.text


def test_a3_pj_expirado_nao_fica_apto():
    ontem = (date.today() - timedelta(days=1)).isoformat()
    result = cadastrar_a3(
        1,
        'TOKEN',
        'PJ',
        '50410847000112',
        'EMPRESA TESTE LTDA',
        'AC TESTE',
        'SERIE-EXP-01',
        '2025-01-01',
        ontem,
        'SHA256withRSA',
        'b' * 64,
        'Token Teste',
        'slot-exp-01',
        1,
    )
    assert result['status'] == 'EXPIRADO'
    assert result['apto_para_uso'] is False
