import importlib.util
from pathlib import Path

BRIDGE_FILE = Path(__file__).with_name('app.py')


def load_bridge(monkeypatch):
    monkeypatch.setenv('OMEGA_BRIDGE_TOKEN', 'test-token')
    monkeypatch.setenv('OMEGA_BRIDGE_ALLOWED_ORIGINS', 'http://localhost:5173')
    monkeypatch.delenv('OMEGA_PKCS11_MODULE', raising=False)
    spec = importlib.util.spec_from_file_location('omega_bridge_app', BRIDGE_FILE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_health_reports_no_pkcs11_without_module(monkeypatch):
    app = load_bridge(monkeypatch)
    result = app.health()
    assert result['status'] == 'ok'
    assert 'pkcs11_configured' in result


def test_windows_candidates_include_valid_safesign(monkeypatch):
    app = load_bridge(monkeypatch)
    monkeypatch.setattr(app.platform, 'system', lambda: 'Windows')
    candidates = app._pkcs11_candidates()
    assert r'C:\Windows\System32\aetpkss1.dll' in candidates
    assert r'C:\Windows\System32\eTPKCS11.dll' in candidates


def test_explicit_module_has_priority(monkeypatch):
    monkeypatch.setenv('OMEGA_BRIDGE_TOKEN', 'test-token')
    monkeypatch.setenv('OMEGA_BRIDGE_ALLOWED_ORIGINS', 'http://localhost:5173')
    monkeypatch.setenv('OMEGA_PKCS11_MODULE', r'C:\custom\middleware.dll')
    spec = importlib.util.spec_from_file_location('omega_bridge_app_explicit', BRIDGE_FILE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    assert module._pkcs11_candidates() == [r'C:\custom\middleware.dll']
