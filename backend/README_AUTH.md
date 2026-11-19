# Autenticação ÔMEGA

A plataforma agora exige autenticação para as APIs de negócio. `GET /health` continua público para monitoramento.

## Usuário inicial

Na primeira inicialização, se ainda não existir nenhum usuário, o sistema cria um administrador com:

- E-mail: `admin@omega.local`
- Senha inicial: `Admin@123`

A primeira entrada exige troca de senha.

Em produção, prefira definir `OMEGA_ADMIN_EMAIL`, `OMEGA_ADMIN_PASSWORD` e `OMEGA_JWT_SECRET` no `.env` antes da primeira execução.

## Perfis

- `ADMIN`: administra usuários e acessa todas as áreas.
- `USUARIO`: acessa as áreas liberadas e não administra usuários.

## Sessão

O access token JWT é enviado no header `Authorization: Bearer <token>`. Cada usuário possui `token_version`; logout e troca de senha incrementam essa versão e invalidam os tokens anteriores.
