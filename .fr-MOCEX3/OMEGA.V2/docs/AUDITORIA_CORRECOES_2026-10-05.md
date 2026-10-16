# ÔMEGA — Correções da Auditoria Técnica

Base: auditoria técnica recebida em 05/10/2026.

## Correções aplicadas nesta versão

1. **Isolamento da suíte de testes (001)**
   - `pytest` agora usa `OMEGA_DB_PATH` e `OMEGA_STORAGE_PATH` de teste antes de importar os módulos.
   - o banco operacional `backend/omega.db` não é usado pela suíte.
   - as fixtures antigas que substituem `database.DB_PATH` continuam funcionando.
   - os testes de autenticação recebem credenciais de teste apenas no ambiente de teste.

2. **Empacotamento seguro (002)
   - criado `scripts/build_release.sh` com exclusão explícita de banco, storage, `.env`, venv, node_modules, caches, logs e arquivos `.bak`.
   - o script falha se encontrar artefatos proibidos dentro do release.

3. **Deploy Docker (003/015)**
   - backend passou a usar `main:app`.
   - `main.py` e `assets/` agora entram na imagem.
   - Playwright Chromium e Tesseract entram no runtime.
   - criado Dockerfile do frontend.
   - `docker-compose.yml` foi alinhado ao entrypoint real.

4. **Configuração (004/022)**
   - `.env` é carregado antes dos módulos que consomem configuração no import.
   - banco e storage podem ser configurados por `OMEGA_DB_PATH` e `OMEGA_STORAGE_PATH`.
   - `VITE_API_URL` representa somente a origem do backend.
   - o cliente normaliza valores antigos que contenham `/api/v1`.
   - removida a construção manual de URL por `:5173/:8000`.

5. **Segurança de autenticação (006/007/026)**
   - não existe mais segredo JWT padrão no código.
   - não existe mais criação automática de administrador com credenciais padrão.
   - exposição do token de reset ficou desativada por padrão e bloqueada em `OMEGA_ENV=production`.
   - adicionado rate limit simples para login e recuperação de senha.

6. **Automações (008/009)**
   - router de automações passou a ser registrado.
   - execução genérica não é mais marcada como concluída sem executar.
   - foram adicionados fluxos reais para sincronização de empresa e consultas de certidões suportadas.
   - falhas ficam registradas como `ERRO`.

7. **Faturamento / Banco do Brasil (010)**
   - cálculo de período voltou a considerar a última competência efetivamente lançada.
   - `detalhamento_disponivel` agora considera a idade da empresa/meses ativos.
   - os 4 cenários do contrato de período voltaram a ficar coerentes com os testes.

8. **Timeouts de automação (011)**
   - chamadas de certidões receberam timeouts específicos maiores que o padrão de 20s.
   - processamento estadual em lote recebeu janela maior.

9. **PDF de certidões (012)**
   - frontend deixou de abrir URL protegida diretamente em `<a>`/`window.open`.
   - agora faz download autenticado, converte para Blob e abre/baixa o arquivo.

10. **OCR/uploads fora do event loop (014/018)**
    - upload/OCR pesado é executado em thread nas rotas async.
    - upload de documentação passou a validar assinatura do conteúdo.
    - MIME não é mais confiado ao `Content-Type` enviado pelo navegador.
    - visualização inline da documentação só ocorre para tipos seguros; demais arquivos são forçados para download.
    - caminho físico de documentação é validado dentro do storage permitido.
    - guias de impostos também validam assinatura PDF/JPG/PNG.

11. **Concorrência de versões (019)**
    - criação de nova versão documental utiliza `BEGIN IMMEDIATE` antes de calcular a próxima versão.

12. **Backup (024)**
    - backup permanente ganhou retenção configurável via `OMEGA_BACKUP_RETENTION` (padrão: 100 arquivos).

13. **Schema (028)**
    - removida duplicidade de índice de faturamentos durante o bootstrap.

## Validação desta versão

- `python -m compileall -q backend`: PASS
- `pytest -q`: **27 passed**
- o banco operacional não foi incluído no release.
- o build completo do frontend não foi concluído neste ambiente porque a instalação das dependências npm expirou; portanto não declarar o frontend como build validado.

## Pendências deliberadamente não mascaradas

Ainda exigem trabalho específico antes de afirmar produção completa:

- **005** — separar migrations/bootstrap do startup;
- **013** — tornar a confirmação da guia uma transação única entre documento, mensal e notificações;
- **016** — arquitetura oficial para automações PyAutoGUI/Windows quando o backend roda em Linux/container;
- **017** — autorização por empresa/recurso (modelo de vínculo usuário↔empresa precisa ser definido);
- **023** — consolidar as duas implementações de API de faturamento;
- **025** — transformar lotes longos em jobs persistentes;
- build E2E/TypeScript completo do frontend em ambiente com dependências npm instaladas.
