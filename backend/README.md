# ÔMEGA — Backend

Backend da Plataforma ÔMEGA construído com FastAPI e SQLite3. A aplicação usa autenticação por bearer token e rotas versionadas em `/api/v1`.

## Considerações arquiteturais
- SQLite é o armazenamento implementado/documentado nesta versão; não assuma PostgreSQL sem validar a adaptação.
- O histórico de certidões e documentos preserva snapshots das consultas.
- Os caminhos relativos de banco e storage são resolvidos contra a pasta do backend, não contra o diretório de execução.
- Em produção, o startup valida segredo JWT, chave Fernet dos certificados, CORS e a existência de um administrador ativo.

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

A Plataforma ÔMEGA possui um fluxo de consulta automatizada à Certidão de Regularidade Fiscal da SEFAZ Pernambuco (e-Fisco) via Playwright. A compatibilidade com o portal deve ser confirmada com teste real antes de uso operacional.

### Instalação

```bash
pip install -r requirements.txt
playwright install chromium
```

### Endpoint principal

`POST /api/v1/certidoes/estadual/consultar/{empresa_id}`

O endpoint consulta o CNPJ cadastrado na empresa, tenta emitir e preservar o PDF no storage configurado, analisa o documento e grava a consulta e o histórico. O armazenamento só é considerado válido quando o caminho está dentro da área de certidões permitida.

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


## Configuração para produção

Veja [docs/PRONTIDAO_PRODUCAO.md](../docs/PRONTIDAO_PRODUCAO.md). Defina chaves próprias em `.env`; não use exemplos como segredos reais. A emissão federal e narrativa ainda utilizam automação visual e precisam de sessão gráfica ativa, navegador e validação com certificado/portal autorizado. Configure SMTP real para habilitar a recuperação de senha por e-mail.
