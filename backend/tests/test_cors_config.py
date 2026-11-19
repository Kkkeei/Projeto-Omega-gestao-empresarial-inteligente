import re

from app.core.cors import development_origin_regex, parse_cors_origins


def test_parse_cors_origins_removes_quotes_spaces_and_duplicates():
    raw = ' http://localhost:5173, http://127.0.0.1:5173, "http://localhost:5173", \'https://omega.example.com\' '
    assert parse_cors_origins(raw) == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://omega.example.com",
    ]


def test_development_cors_accepts_local_lan_and_production_disables_regex():
    pattern = development_origin_regex("development")
    assert pattern is not None
    assert re.fullmatch(pattern, "http://192.168.0.130:5173")
    assert re.fullmatch(pattern, "http://localhost:5173")
    assert not re.fullmatch(pattern, "https://public.example.com:5173")
    assert development_origin_regex("production") is None


def test_login_preflight_from_local_network_is_accepted():
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://192.168.0.130:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://192.168.0.130:5173"
