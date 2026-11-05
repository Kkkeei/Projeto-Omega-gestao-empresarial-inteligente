# Módulo Contábil — Contrato de backend

**Status:** especificação para implementação do backend.  
**Frontend:** implementado na branch `feat/contabil-frontend-foundation`.  
**Prefixo da API:** `/api/v1/contabil`.

Este documento define os contratos que o backend deverá implementar para atender ao frontend Contábil. Os endpoints descritos abaixo ainda precisam ser implementados e registrados no FastAPI; não considerar que já estejam disponíveis no ambiente.

## 1. O que já existe e deve ser reaproveitado

A inspeção do código do repositório confirmou:

| Estrutura | Local / nome | Decisão |
|---|---|---|
| Cadastro de empresas | tabela `empresas` | Reutilizar. Não criar cópia. |
| Cadastro de usuários | tabela `usuarios` | Reutilizar. Responsável é um usuário ativo existente. |
| Autenticação | `app.api.v1.auth.routes.current_user` | Aplicar em todas as rotas privadas. |
| Auditoria global | tabela `auditorias` | Registrar operações também na trilha global, conforme padrão do projeto. |
| Conexão SQLite | `app.db.database.conectar_banco` | Reutilizar. |
| Storage configurável | `app.db.database.STORAGE_BASE` | Reutilizar como raiz de arquivos. |
| Documentação atual | `app.modules.documentacao` | Preservar: é o Dossiê Digital, baseado em documentos e versões. |
| Rotas centrais | `app.api.v1.routes.router` | Incluir o novo router contábil. |
| Frontend atual | React Router, `apiFetch`, CSS global | Reutilizar. |

### Por que o Contábil terá tabelas próprias

O módulo `documentacao` atual utiliza `documentos`, `categorias_documentos` e `documento_versoes`. O cadastro existente representa um documento digital e suas versões.

No Contábil, o cadastro representa uma obrigação recorrente. Um único cadastro, como um extrato bancário, precisa produzir obrigações independentes em agosto, setembro, outubro e nos meses posteriores. Cada competência tem seu próprio status e conjunto de arquivos.

Não usar a tabela `documentos` como cadastro recorrente e não alterar a semântica do Dossiê Digital. O novo módulo usa tabelas `contabil_*`, mas reaproveita empresas, usuários, autenticação, auditoria geral e storage.

## 2. Arquivos do frontend

| Arquivo | Responsabilidade |
|---|---|
| `frontend/src/modules/contabil/ContabilPage.tsx` | Dashboard por regime, pesquisa, status e acesso às empresas. |
| `frontend/src/modules/contabil/AtribuicaoModal.tsx` | Distribuição e transferência de empresas entre responsáveis. |
| `frontend/src/modules/contabil/EmpresaContabilPage.tsx` | Competências, pastas, documentações, upload e inativação. |
| `frontend/src/modules/contabil/ContabilLancamentosPage.tsx` | Área de Lançamentos e Conferências, ainda em planejamento. |
| `frontend/src/modules/contabil/contabilApi.ts` | Chamadas HTTP e contratos de API. |
| `frontend/src/modules/contabil/types.ts` | Tipos TypeScript compartilhados. |
| `frontend/src/modules/contabil/contabil.css` | Estilos locais do módulo. |

Rotas de frontend:
- `/contabil`
- `/contabil/documentacao`
- `/contabil/documentacao/empresa/:id`
- `/contabil/lancamentos-conferencias`

O menu antigo de Documentação foi renomeado visualmente para **Dossiê Digital**, mantendo o caminho `/documentacao` e suas rotas existentes.

## 3. Banco de dados

O SQL inicial está em:

`docs/sql/contabil_schema_sqlite.sql`

Ele cria:

| Tabela | Uso |
|---|---|
| `contabil_atribuicoes` | Histórico de vigência de responsáveis por empresa. |
| `contabil_atribuicoes_historico` | Transferências e retiradas de responsabilidade. |
| `contabil_categorias` | Pastas contábeis por empresa. |
| `contabil_documentos` | Cadastros permanentes de documentos recorrentes. |
| `contabil_obrigacoes` | Uma obrigação por documento e competência. |
| `contabil_arquivos` | Arquivos recebidos por obrigação, com exclusão lógica. |
| `contabil_historico` | Linha do tempo das operações do módulo por empresa. |

### Regras estruturais

1. Uma empresa tem no máximo uma atribuição principal ativa. O índice único parcial de `contabil_atribuicoes` impede duas atribuições com `encerrado_em IS NULL`.
2. Usuários e empresas são referenciados pelas chaves existentes.
3. Categorias são específicas por empresa. A pasta virtual **Tudo** não é gravada.
4. Um documento recorrente gera no máximo uma obrigação por competência: `UNIQUE(documento_id, competencia)`.
5. Arquivos não devem ser apagados fisicamente no fluxo comum de exclusão. Preencher `excluido_em`, `excluido_por` e `motivo_exclusao`.
6. Inativar documento não apaga obrigações ou arquivos anteriores. A competência final é inclusiva.
7. `status` não é persistido em `contabil_obrigacoes`; é calculado pelo serviço considerando arquivos ativos e a competência.
8. Não excluir empresa, usuário, documento ou categoria com histórico vinculado. Inativar/arquivar conforme o caso.
9. Cada alteração importante gera um registro em `contabil_historico` e, quando aplicável, em `auditorias`.

### Categorias iniciais por empresa

Criar de forma idempotente, na primeira consulta ou pelo serviço de inicialização da documentação:

1. Extratos Bancários
2. Aplicações Financeiras
3. Financiamentos / Empréstimos
4. Consórcios
5. Administradoras de Cartões
6. Outros Documentos

Se já houver categorias ativas, não duplicar os nomes. As categorias personalizadas também devem ser preservadas.

### Geração das obrigações mensais

Ao consultar a competência `YYYYMM`:

1. Validar se a empresa existe.
2. Garantir categorias padrão.
3. Buscar cadastros cujo início seja menor ou igual à competência e cujo fim seja nulo ou maior/igual à competência.
4. Criar, com inserção idempotente, a obrigação para cada cadastro aplicável.
5. Não criar obrigações anteriores ao início nem posteriores à competência final.
6. Retornar documento e obrigação com a quantidade de arquivos ativos e a data do último upload.

A criação sob demanda evita depender de uma rotina mensal agendada para que a interface apresente as obrigações. A restrição única impede duplicação caso dois usuários consultem a mesma competência simultaneamente.

### Cálculo de status

Status individual:

| Condição | Status de API | Rótulo de UI |
|---|---|---|
| Existe ao menos um arquivo ativo | `RECEBIDO` | Recebido |
| Sem arquivo e competência posterior à atual | `FUTURO` | Futura |
| Sem arquivo e competência igual à atual | `PENDENTE` | Pendente |
| Sem arquivo e competência anterior à atual | `NAO_RECEBIDO` | Não recebido |

Status agregado da empresa:
- `COMPLETA`: existe ao menos uma obrigação e todas estão recebidas.
- `PARCIAL`: pelo menos uma obrigação recebida e pelo menos uma pendente/não recebida.
- `SEM_RECEBIMENTO`: nenhuma obrigação foi recebida.

O status anual de cada mês utiliza `COMPLETA`, `PARCIAL`, `SEM_RECEBIMENTO` ou `FUTURA`. Para mês futuro, usar `FUTURA`; para mês passado sem recebimento, usar `SEM_RECEBIMENTO`; para competência atual sem recebimento, usar `PARCIAL` para sinalizar pendência amarela na timeline.

## 4. Contratos HTTP

Todas as rotas exigem `Authorization: Bearer <token>` por meio de `current_user`.

Os campos de usuário e empresa sempre usam os IDs das tabelas existentes.

### 4.1 Dashboard e listagem

#### GET `/dashboard`

Query:
- `competencia`: inteiro `YYYYMM`, obrigatório.
- `busca`: razão social, nome fantasia ou CNPJ.
- `regime`: `SIMPLES NACIONAL`, `LUCRO PRESUMIDO`, `LUCRO REAL`.
- `responsavel_id`: ID do usuário.
- `sem_responsavel`: booleano.
- `pagina`: padrão 1.
- `por_pagina`: padrão 100, limite recomendado 200.

Retorno:
§json
{
  "competencia": 202611,
  "resumo": {
    "total_empresas": 23,
    "simples_nacional": 12,
    "lucro_presumido": 8,
    "lucro_real": 3,
    "documentacao_completa": 8,
    "documentacao_parcial": 10,
    "sem_recebimento": 5
  },
  "empresas": [
    {
      "id": 41,
      "razao_social": "Empresa Exemplo LTDA",
      "nome_fantasia": "Exemplo",
      "cnpj": "12345678000190",
      "regime_tributario": "SIMPLES NACIONAL",
      "ativo": true,
      "documentos_recebidos": 2,
      "documentos_total": 5,
      "status_documentacao": "PARCIAL",
      "responsavel_id": 12,
      "responsavel_nome": "Anderson"
    }
  ],
  "total": 23,
  "pagina": 1,
  "por_pagina": 100
}
§

Os valores acima são ilustrativos. O backend calcula os totais com base nas empresas e obrigações reais. A listagem deve ser ordenada por razão social.

#### GET `/empresas`

Usada pela tela de atribuição. Query: `busca`, `regime`, `incluir_inativas=false`.

Retorno: `{ "empresas": EmpresaContabil[] }`. Cada empresa deve conter os campos do dashboard, incluindo `responsavel_id` e `responsavel_nome`.

### 4.2 Responsáveis e atribuições

#### GET `/responsaveis`

Listar usuários ativos que podem receber empresas e a quantidade de atribuições ativas:

§json
{
  "responsaveis": [
    {
      "id": 12,
      "nome": "Anderson",
      "email": "anderson@example.com",
      "perfil": "USUARIO",
      "ativo": true,
      "empresas_atribuidas": 8
    }
  ]
}
§

Não criar uma tabela paralela de responsáveis nem usuários fixos. Anderson e Kamily são usuários existentes; os registros reais devem vir de `usuarios`.

#### POST `/atribuicoes/lote`

Aplicar alterações de atribuição dentro de uma única transação. Se uma operação falhar, desfazer o lote inteiro.

Request:
§json
{
  "alteracoes": [
    {
      "empresa_id": 41,
      "responsavel_id": 12,
      "confirmar_transferencia": false,
      "motivo": "Atribuição pela tela Contábil"
    },
    {
      "empresa_id": 42,
      "responsavel_id": null,
      "confirmar_transferencia": false,
      "motivo": "Retirada da carteira pela tela Contábil"
    }
  ]
}
§

Regras:
- Validar empresas e usuários.
- O novo usuário deve estar ativo.
- Se houver responsável ativo diferente, exigir `confirmar_transferencia=true`.
- Encerrar atribuição anterior, inserir nova atribuição e inserir histórico.
- Para retirar, encerrar a atribuição ativa sem criar atribuição nova.
- Registrar usuário autenticado como `atribuido_por`/autor da operação.
- Retornar `{ "alteradas": number, "atribuicoes": [...] }`.
- Responder HTTP 409 quando houver conflito de transferência não confirmado.

### 4.3 Documentação por empresa

#### GET `/empresas/{empresa_id}/documentacao?competencia=YYYYMM&ano=YYYY`

Retornar:
- dados cadastrais mínimos da empresa;
- categorias ativas;
- documentos aplicáveis à competência e obrigações correspondentes;
- status de cada obrigação;
- quantidade de arquivos ativos e data/hora do último upload;
- resumo da competência;
- `competencias_ano` com situação dos doze meses para pintar a timeline.

Exemplo de envelope:
§json
{
  "empresa": {
    "id": 41,
    "razao_social": "Empresa Exemplo LTDA",
    "nome_fantasia": "Exemplo",
    "cnpj": "12345678000190",
    "regime_tributario": "LUCRO REAL"
  },
  "competencia": 202611,
  "competencias_ano": [
    { "mes": 1, "status": "COMPLETA" },
    { "mes": 2, "status": "PARCIAL" },
    { "mes": 3, "status": "FUTURA" }
  ],
  "categorias": [
    {
      "id": 1,
      "empresa_id": 41,
      "nome": "Extratos Bancários",
      "descricao": null,
      "ordem": 1,
      "ativo": true,
      "documentos_count": 4,
      "obrigacoes_pendentes": 1,
      "obrigacoes_recebidas": 3
    }
  ],
  "documentos": [
    {
      "id": 25,
      "empresa_id": 41,
      "categoria_id": 1,
      "categoria_nome": "Extratos Bancários",
      "nome": "Banco Sicoob CC 159.522-9",
      "observacao": "Agência 0001",
      "competencia_inicio": 202608,
      "competencia_fim": null,
      "ativo": true,
      "obrigacao_id": 125,
      "status": "PENDENTE",
      "quantidade_arquivos": 0,
      "ultimo_upload": null
    }
  ],
  "resumo": {
    "total": 5,
    "recebidos": 2,
    "pendentes": 2,
    "nao_recebidos": 1
  }
}
§

Os campos `documentos_count`, `obrigacoes_pendentes` e `obrigacoes_recebidas` devem ser calculados para a competência consultada. `competencias_ano` deve conter os doze meses.

#### POST `/empresas/{empresa_id}/categorias`

Request: `{ "nome": string, "descricao": string | null }`. Criar pasta ativa para a empresa.

#### PATCH `/categorias/{categoria_id}`

Request: `{ "nome": string, "descricao": string | null }`. Atualizar sem alterar IDs ou caminhos de storage.

#### DELETE `/categorias/{categoria_id}`

Arquivar logicamente. Recusar exclusão quando houver documentos ou histórico vinculado; não apagar fisicamente registros.

### 4.4 Cadastro recorrente

#### POST `/empresas/{empresa_id}/documentos`

Request:
§json
{
  "nome": "Banco Sicoob CC 159.522-9",
  "categoria_id": 1,
  "competencia_inicio": 202608,
  "observacao": "Agência 0001"
}
§

Criar cadastro e obrigação inicial na competência informada. Demais competências são geradas na consulta. Retornar `DocumentoContabil`.

#### PATCH `/documentos/{documento_id}`

Request: `{ "nome": string, "categoria_id": number, "observacao": string | null }`.

A competência inicial não é alterada pelo formulário de edição atual. Caso o backend disponibilize alteração futura de início/fim, exigir confirmação se já houver obrigações e preservar o histórico.

#### POST `/documentos/{documento_id}/inativar`

Request:
§json
{
  "competencia_fim": 202610,
  "motivo": "Conta encerrada",
  "observacao": "Encerramento da conta bancária"
}
§

A competência final é inclusiva. A partir da competência seguinte, não criar novas obrigações. Preservar o cadastro, as obrigações anteriores, os arquivos e o histórico.

### 4.5 Arquivos da obrigação

#### GET `/obrigacoes/{obrigacao_id}/arquivos`

Retornar `{ "arquivos": ArquivoContabil[] }`, ordenados por upload decrescente, sem registros logicamente excluídos.

#### POST `/obrigacoes/{obrigacao_id}/arquivos`

Content type: `multipart/form-data`. O frontend envia múltiplos arquivos usando o mesmo campo `arquivos`.

Validações:
- extensões permitidas: PDF, JPG, JPEG, PNG, XLSX;
- limite de 25 MB por arquivo;
- validar conteúdo/MIME real, não confiar somente no nome;
- gerar nome físico aleatório, não usar nome do cliente como caminho;
- calcular SHA-256;
- gravar no storage configurado e registrar caminho relativo;
- inserir metadados apenas depois de validar e gravar o arquivo;
- registrar usuário, data e auditoria;
- em erro parcial, retornar quais arquivos falharam e evitar registros órfãos.

Pasta física sugerida:
`STORAGE_BASE/contabil/documentos/{empresa_id}/{competencia}/{obrigacao_id}/`

Retorno: `{ "arquivos": ArquivoContabil[] }`, contendo a lista atualizada.

#### PATCH `/arquivos/{arquivo_id}`

Request: `{ "nome": string }`. Alterar apenas nome de exibição; preservar caminho físico e histórico.

#### DELETE `/arquivos/{arquivo_id}`

Request opcional: `{ "motivo": string | null }`. Exclusão lógica. Recalcular status da obrigação após a operação.

#### GET `/arquivos/{arquivo_id}/download`

Retornar `FileResponse`, conferindo que o caminho resolvido está dentro de `STORAGE_BASE`. Registrar acesso conforme as convenções de auditoria do projeto.

### 4.6 Histórico

#### GET `/empresas/{empresa_id}/historico`

Retornar eventos de `contabil_historico` em ordem decrescente, com usuário, entidade, ação, competência quando aplicável e dados resumidos. Filtrar por empresa.

Registrar no mínimo:
- atribuições e transferências;
- cadastro/edição/inativação de documentação;
- criação/edição/arquivamento de pasta;
- upload, renomeação e exclusão lógica de arquivo.

## 5. Formato de tipos da API

O frontend usa os tipos em `types.ts`. Atenção para:
- IDs como números;
- booleanos JSON para flags (`ativo`);
- competência como inteiro `YYYYMM`;
- timestamps ISO-8601;
- campos opcionais explicitamente como `null` quando aplicável;
- enums de status exatamente como definidos neste documento.

Não enviar valores de `regime_tributario` transformados ou abreviados; preservar os valores existentes em `empresas` e normalizar somente na comparação.

## 6. Estrutura sugerida do backend

Criar o módulo conforme o padrão atual de módulos FastAPI:

§text
backend/app/modules/contabil/
├── __init__.py
├── routes.py
├── schemas.py
└── service.py
§

Se o módulo crescer, separar em subpastas `routes/`, `services/`, `models/` e `schemas/`. Não adicionar ORM caso o restante do backend continue usando `sqlite3` diretamente; manter a mesma abstração `conectar_banco()`.

### Registro do router

Em `backend/app/api/v1/routes.py`:
1. Importar `router` de `app.modules.contabil.routes`.
2. Executar `router.include_router(contabil_router)`.
3. Não repetir o `Depends(current_user)` se as rotas individuais já aplicarem a dependência; seguir o padrão atual do router principal.

Todas as rotas devem validar a empresa e os registros vinculados. Em downloads, aplicar a mesma proteção de path traversal existente em `app.modules.documentacao.routes`.

## 7. Testes de backend obrigatórios

- Dashboard com empresas de todos os regimes e empresa sem responsável.
- Pesquisa por razão social, nome fantasia e CNPJ.
- Filtros de regime e responsável combinados.
- Listagem de usuários ativos sem duplicar cadastros.
- Duas atribuições concorrentes para a mesma empresa.
- Transferência confirmada e tentativa sem confirmação.
- Registro de histórico anterior e novo responsável.
- Criação idempotente de categorias padrão.
- Cadastro de documento e primeira obrigação.
- Consulta repetida da mesma competência sem duplicação.
- Não criar obrigações antes da competência inicial.
- Competência final inclusiva e sem geração posterior.
- Status recebido, pendente, não recebido e futuro.
- Upload múltiplo com um arquivo inválido.
- Rejeição de arquivo acima de 25 MB ou extensão não permitida.
- Exclusão lógica e retorno ao status pendente.
- Download impedindo caminho fora do storage.
- Usuário inativo não pode assumir novas empresas.
- Histórico preservado após inativação de usuário, documento ou categoria.

## 8. Ordem de integração

1. Fazer backup de `backend/omega.db` e `storage/`.
2. Revisar/aplicar `docs/sql/contabil_schema_sqlite.sql` como migration controlada.
3. Implementar schemas e serviços.
4. Implementar rotas e registrar router.
5. Testar endpoints isoladamente com token real de usuário de teste.
6. Validar contratos contra `contabilApi.ts`.
7. Testar o frontend com backend conectado.
8. Somente depois considerar a integração futura com Lançamentos e Conferências.

**Importante:** o SQL é uma proposta inicial compatível com o SQLite atual. Não executá-lo sobre banco de produção sem backup, inspeção de versão e revisão de integridade. Nenhuma tabela deste documento foi criada no banco pelo trabalho de frontend.
