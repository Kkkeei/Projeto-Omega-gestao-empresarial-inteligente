# ÔMEGA — Plataforma de Gestão Empresarial

V2 criada a partir dos documentos de requisitos e da base real `dados/CADASTRO.xlsx`.

## Subir backend com Uvicorn

```bash
cd backend
source /run/media/davi/PROJETOS/meu_venv/bin/activate
pip install -r requirements.txt
# confirme o DATABASE_URL no .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger: http://localhost:8000/docs
Health: http://localhost:8000/health

## Importar as empresas da CADASTRO.xlsx

Com o PostgreSQL e o banco `omega` criados:

```bash
cd backend
python scripts/importar_cadastro.py
```

O importador usa o CNPJ como chave, não duplica registros e marca a origem como `IMPORTACAO_CADASTRO`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

O frontend usa `VITE_API_URL` e, por padrão, aponta para `http://localhost:8000/api/v1`.

## Desenvolvimento local — SQLite

Esta versão usa SQLite por simplicidade no desenvolvimento e na apresentação. Não é necessário instalar PostgreSQL.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Banco criado automaticamente em `backend/omega.db`.

### Importar CADASTRO.xlsx

Com o backend instalado:

```bash
cd backend
python scripts/importar_cadastro.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

O frontend usa os dados de demonstração enquanto a integração com a API não estiver conectada.

## Proteção do banco de dados na instalação

O pacote distribuído é **source-only** e **não contém `backend/omega.db` nem backups SQLite**. Ao descompactar/atualizar o projeto em um servidor que já possui dados, o banco existente não é substituído pelo pacote.

O backend usa `backend/omega.db` como arquivo de dados. A rotina `criar_tabelas()` cria apenas tabelas/índices que ainda não existem e não executa `DROP`, `DELETE` ou substituição do banco.

**Regra de implantação:** descompacte o projeto sobre a instalação existente e mantenha o `backend/omega.db` do servidor. Não copie um banco de demonstração por cima do banco operacional.

O `.gitignore` também bloqueia `*.db`, `*.sqlite` e `*.sqlite3` para reduzir o risco de versionar ou distribuir dados reais.

## Certidão Estadual — SEFAZ-PE

A Plataforma ÔMEGA agora possui integração do módulo de Certidões com a Certidão de Regularidade Fiscal da SEFAZ Pernambuco/e-Fisco.

Fluxo: Empresa → Certidões → Certidão Estadual → Consultar → Playwright/e-Fisco → PDF → análise → banco/histórico → visualização.

No backend, instale as dependências com `pip install -r backend/requirements.txt` e o navegador com `playwright install chromium`.

## Persistência permanente de certidões

O módulo de certidões mantém um histórico fiscal permanente e append-only. Cada consulta gera um registro em `consultas_certidoes` e um snapshot imutável em `certidoes_historico`. PDFs são armazenados com nome único e hash SHA-256, sem sobrescrever versões anteriores.

A base SQLite usa WAL + `synchronous=FULL` e, após cada consulta registrada, o sistema cria uma cópia consistente e não sobrescrita em `storage/backups/database/AAAA/MM/`. Consultas, snapshots e documentos de certidão não podem ser apagados por SQL; a exclusão de uma empresa que possua histórico de certidões também é bloqueada.

## Proteção contra consultas simultâneas

A Central de Certidões agora usa um lock distribuído persistido no SQLite (`automacao_locks`). Como as automações visuais utilizam PyAutoGUI e controlam a sessão gráfica do Windows, somente uma automação de certidão pode executar por vez no servidor.

- Segunda tentativa recebe HTTP 409 com mensagem amigável.
- O lock funciona entre usuários e entre processos/workers do FastAPI.
- O lock é liberado automaticamente ao concluir ou falhar a automação.
- Locks abandonados por encerramento inesperado expiram automaticamente após o TTL configurado (`OMEGA_AUTOMACAO_LOCK_TTL_MINUTES`, padrão 240 minutos).
- Endpoint de status: `GET /api/v1/certidoes/automacao/status`.
- A interface consulta o status periodicamente e desabilita os botões enquanto outra automação estiver em execução.

Essa proteção é necessária porque PyAutoGUI opera no teclado/mouse da máquina inteira e duas automações simultâneas poderiam misturar janelas, teclas, cliques e certificados.

## Autenticação V5

A plataforma possui fluxo completo de acesso:

- Entrar
- Criar conta
- Esqueci minha senha
- Redefinir senha por token de uso único
- Alterar senha autenticado
- Logout
- Perfis ADMIN e USUARIO
- Administração de usuários
- Revogação de sessões
- Auditoria de autenticação

Rotas públicas do frontend: `/login`, `/registrar`, `/esqueci-senha`, `/redefinir-senha`.


## Diagnóstico do cadastro
O endpoint público de criação de conta é `POST /api/v1/auth/registrar`. Em desenvolvimento, o Vite faz proxy de `/api` para `http://127.0.0.1:8000`, evitando inconsistências de `VITE_API_URL`.


## Módulo Documentação

Implementada a área Documentação conforme os requisitos e UML entregues: empresas em cards compactos, filtros por regime, pastas por tipo de documento (Societário, Pessoal (Sócio), Imposto de Renda), categorias dinâmicas, upload, download, visualização e histórico de versões. Os PDFs de especificação ficam em `docs/especificacoes_documentacao/`.


## Documentação — estrutura atual

A área Documentação segue uma estrutura inspirada no Explorador de Arquivos do Windows. Cada empresa possui somente três pastas visíveis e oficiais: **Pessoal (Sócio)**, **Societário** e **IRPF**. Categorias antigas ou extras são arquivadas e não aparecem na navegação.
