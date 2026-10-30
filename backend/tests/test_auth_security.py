import pytest

from app.services import auth_service


def test_jwt_secret_rejects_empty_and_sample_values(monkeypatch):
    monkeypatch.setenv("OMEGA_JWT_SECRET", "")
    with pytest.raises(RuntimeError, match="chave aleatória própria"):
        auth_service._secret()

    monkeypatch.setenv("OMEGA_JWT_SECRET", "GERE_UMA_CHAVE_ALEATORIA_COM_NO_MINIMO_32_CARACTERES")
    with pytest.raises(RuntimeError, match="chave aleatória própria"):
        auth_service._secret()


def test_jwt_secret_accepts_a_configured_long_secret(monkeypatch):
    secret = "ci-test-random-secret-with-more-than-thirty-two-characters"
    monkeypatch.setenv("OMEGA_JWT_SECRET", secret)
    assert auth_service._secret() == secret


def test_password_reset_email_does_not_return_secret_when_smtp_missing(monkeypatch):
    for key in ("OMEGA_SMTP_HOST", "OMEGA_SMTP_FROM", "OMEGA_FRONTEND_URL"):
        monkeypatch.delenv(key, raising=False)
    assert auth_service.enviar_email_redefinicao("user@example.com", "Usuário", "token-de-teste") is False


def test_production_rejects_public_registration(monkeypatch):
    from cryptography.fernet import Fernet

    monkeypatch.setenv("OMEGA_ENV", "production")
    monkeypatch.setenv("OMEGA_JWT_SECRET", "prod-random-secret-not-for-ci-0123456789")
    monkeypatch.setenv("OMEGA_CERTIFICADO_MASTER_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("CORS_ORIGINS", "https://omega.example.com")
    monkeypatch.setenv("OMEGA_PUBLIC_REGISTRATION", "true")

    with pytest.raises(RuntimeError, match="OMEGA_PUBLIC_REGISTRATION deve ser false"):
        auth_service.validar_configuracao_producao()
