# Correções de login e visibilidade de empresas — 13/11/2026

## Correções aplicadas

1. **CORS / preflight do login**
   - A lista `CORS_ORIGINS` agora remove espaços, aspas acidentais e duplicidades.
   - Em ambiente diferente de produção, o backend aceita o frontend Vite na porta 5173 quando acessado por `localhost`, `127.0.0.1` ou IP IPv4 privado da rede local.
   - Em produção, essa permissão por regex local fica desativada; as origens precisam estar declaradas em `CORS_ORIGINS`.

2. **Conta administrativa configurada**
   - Se o e-mail configurado em `OMEGA_ADMIN_EMAIL` já existir com perfil `USUARIO` ou estiver inativo, o bootstrap corrige o perfil para `ADMIN` e reativa a conta.
   - A senha já cadastrada não é substituída automaticamente.
   - Isso evita que a conta de administração local seja tratada como usuário comum e tenha a visualização de empresas limitada às atribuições.

3. **BrasilAPI**
   - Corrigida a importação de `json` usada ao converter respostas JSON malformadas em erro controlado.

4. **Aviso de inicialização da NFS-e**
   - O aviso de nível `WARNING` foi substituído por uma mensagem informativa. A rotina automática ainda não está implementada nesta versão; consultas continuam sob demanda. Nenhuma rotina fictícia foi criada e o backend não tenta usar cartões A3 fisicamente no servidor.

## Validação

- Testes focados de CORS, preflight, bootstrap administrativo, painel Contábil e resposta inválida da BrasilAPI: aprovados.
- Testes focados (CORS/preflight, bootstrap administrativo, Contábil, Documentação, BrasilAPI e Certificados): **39 aprovados**.
- Suíte backend completa: **99 aprovados e 6 falhas** em testes de funções NFS-e ainda ausentes nesta versão (`painel`, `importar_xml_manual`, `importar_email_eml`, `_request_a1_url` e `importar_eventos_a3`). Essas funções estão descritas no documento legado de implementação do painel NFS-e, mas não existem no serviço atual; não foram simuladas nesta correção.
- O teste antigo que exigia thumbprint obrigatório no cadastro declarativo A3 foi atualizado para validar o fluxo atual: A3 pode ser cadastrado sem vínculo técnico e fica `NAO_VINCULADO` até a detecção pelo Bridge.
- O build completo do frontend não foi executado: `npm ci --offline` não encontrou um pacote no cache local (`yallist`). Não houve alteração no código do frontend.

## Segurança

- Não distribua `backend/.env` real. Use `backend/.env.example` como modelo.
- Como uma captura de tela exibiu valores de credenciais e chave mestre, considere a senha administrativa exposta e altere-a.
- A chave mestre de certificados A1 não deve ser trocada diretamente em uma instalação com PFX já armazenado: a troca sem migração criptográfica torna os arquivos antigos indecifráveis. Faça backup de banco e storage e planeje a rotação/recriptografia antes de alterar a chave.
- Deixe `OMEGA_RESET_EXPOSE_URL=false` e use `OMEGA_ENV=production` fora do ambiente de desenvolvimento.
