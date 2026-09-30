from app.api.v1.auth.routes import register, forgot_password, reset_password, RegisterIn, ForgotPasswordIn, ResetPasswordIn
from app.services.auth_service import buscar_usuario_por_id, verify_password


def test_register_and_reset_flow():
    result = register(RegisterIn(nome="Usuário Teste", email="teste.auth@example.com", senha="SenhaTeste123", confirmar_senha="SenhaTeste123"))
    assert result["ok"] is True
    user = result["usuario"]
    assert user["perfil"] == "USUARIO"

    forgot = forgot_password(ForgotPasswordIn(email="teste.auth@example.com"))
    assert forgot["ok"] is True
    assert "reset_token" in forgot

    reset = reset_password(ResetPasswordIn(token=forgot["reset_token"], nova_senha="NovaSenha123", confirmar_senha="NovaSenha123"))
    assert reset["ok"] is True

    stored = buscar_usuario_por_id(user["id"])
    assert stored is not None
    assert verify_password("NovaSenha123", stored["senha_hash"])
