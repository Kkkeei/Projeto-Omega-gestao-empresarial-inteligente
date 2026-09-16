# Autenticação, cadastro e recuperação de acesso — ÔMEGA

## Fluxos implementados

- Login por e-mail e senha
- Criar conta
- Logout
- Sessão JWT
- Alterar senha autenticado
- Esqueci minha senha
- Redefinir senha com token de uso único e validade configurável
- Perfis ADMIN e USUARIO
- Gestão administrativa de usuários
- Revogação de sessões
- Troca obrigatória de senha do administrador inicial
- Auditoria de login, logout, registro e redefinição

## Primeiro acesso

Por padrão é criado:

- e-mail: `admin@omega.local`
- senha: `Admin@123`

A primeira entrada exige troca de senha.

## Desenvolvimento

`OMEGA_RESET_EXPOSE_URL=true` faz a API devolver o link/token de redefinição para o frontend, útil para desenvolvimento local sem servidor de e-mail.

## Produção

Defina:

```env
OMEGA_RESET_EXPOSE_URL=false
```

E conecte um provedor SMTP/e-mail transacional ao fluxo `/api/v1/auth/esqueci-senha`. A resposta pública continua genérica para evitar enumeração de e-mails.
