# ÔMEGA — Backend MVP

Backend inicial funcional da Plataforma ÔMEGA, construído com FastAPI + SQLite3 puro.

## Decisões
- Sem login/usuários na primeira versão.
- Sem SQLAlchemy.
- Sem Alembic.
- Histórico funcional sem sobrescrever consultas/documentos.
- API versionada em `/api/v1`.
- CORS preparado para frontend Vite em `localhost:5173`.

## Executar

```bash
python -m app.db.database
uvicorn main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`

## Endpoints MVP

- `GET /health`
- `GET /api/v1/dashboard/resumo`
- `GET /api/v1/empresas`
- `POST /api/v1/empresas`
- `GET /api/v1/empresas/{id}`
- `PUT /api/v1/empresas/{id}`
- `POST /api/v1/empresas/{id}/inativar`
- `POST /api/v1/empresas/{id}/regime`
- `GET /api/v1/empresas/{id}/historico`
- `GET /api/v1/empresas/cnpj/{cnpj}/consulta`
- `POST /api/v1/empresas/{id}/sync`
- `GET /api/v1/certidoes`
- `POST /api/v1/certidoes`
- `GET /api/v1/certidoes/tipos`
- `GET /api/v1/certidoes/empresa/{id}/historico`
- `GET /api/v1/pendencias`
- `POST /api/v1/pendencias`
- `PATCH /api/v1/pendencias/{id}`
- `POST /api/v1/automacoes/executar`
- `POST /api/v1/automacoes/executar/{tipo}`
- `GET /api/v1/automacoes/execucoes`

## Próximas integrações

As consultas de certidões reais, Playwright e outras integrações externas devem ser implementadas como adaptadores próprios. O MVP não deve fingir uma consulta oficial que ainda não foi implementada.

## Certidão Estadual — SEFAZ-PE

A Plataforma ÔMEGA possui consulta integrada à Certidão de Regularidade Fiscal da SEFAZ Pernambuco (e-Fisco) via Playwright.

### Instalação

```bash
pip install -r requirements.txt
playwright install chromium
```

### Endpoint principal

`POST /api/v1/certidoes/estadual/consultar/{empresa_id}`

O endpoint consulta o CNPJ cadastrado na empresa, emite a certidão, preserva o PDF em `storage/certidoes/estadual/{cnpj}/{ano}/`, analisa a situação e grava a consulta e seu histórico.

### Visualização de PDF

`GET /api/v1/certidoes/pdf?path=<caminho_relativo>`

### Estados fiscais

- `REGULAR`
- `POSITIVA COM EFEITOS DE NEGATIVA`
- `IRREGULAR`
- `NAO IDENTIFICADO`
- `AGUARDANDO_INTERVENCAO`
- `ERRO`

`IRREGULAR` representa uma situação fiscal retornada pela certidão e não um erro técnico.
