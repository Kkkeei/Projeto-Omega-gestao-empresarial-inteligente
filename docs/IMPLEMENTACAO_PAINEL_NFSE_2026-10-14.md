# Implementação do painel NFS-e — 14/10/2026

## Escopo

Implementação no módulo NFS-e existente, preservando a arquitetura FastAPI + React/TypeScript e o SQLite atual. O código cria tabelas novas de forma idempotente (`CREATE TABLE IF NOT EXISTS`) e não substitui nem recria tabelas de empresas, titulares, certificados ou documentos existentes.

## Recursos incluídos

- Painel do escritório com filtro por competência, pesquisa por empresa/documento, filtros de status, quantidades de NFS-e prestadas/tomadas, total financeiro, cancelamentos e última sincronização.
- Abertura de cada titular com abas e filtros de documentos prestados/tomados, origem do documento e extração de dados fiscais encontrados no XML.
- Status por empresa: OK, Pendente, Erro, Sem movimento e Sincronizando, com mensagem explicativa.
- Importação manual de XML (limite de 10 MB) e importação de anexos XML de e-mails salvos em `.eml` (limite de 20 MB por mensagem e até 50 anexos), além da importação ADN/A1 e fluxo A3/Bridge já existente.
- Exportação XLSX por competência e por titular opcional.
- Download de XMLs selecionados em ZIP (máximo de 200 arquivos por lote).
- Sincronização manual em lote com status e progresso persistidos.
- Configuração de sincronização automática por titular, desativada por padrão, com frequência de 1 hora, 6 horas ou diariamente em horário configurado.
- Histórico de sincronização e alertas para falhas, pendências, sem movimento, retenções, certificados expirados e possíveis lacunas de numeração.
- Checklist de fechamento por competência e titular, com observações persistidas. O fechamento exige todas as confirmações e nenhum XML inválido.
- Histórico de eventos por NFS-e, consulta de eventos oficiais do ADN por certificado A1 ou Bridge A3, consulta pública oficial para DANFSe pela chave de acesso e rascunho de vínculo contábil com contas, data, histórico e valor.

## Endpoints adicionados/estendidos

- `GET /api/v1/nfse/painel`
- `GET /api/v1/nfse/resumo`
- `GET/PUT /api/v1/nfse/configuracao`
- `GET /api/v1/nfse/historico`
- `GET /api/v1/nfse/alertas`
- `GET/PUT /api/v1/nfse/competencia/fechamento`
- `POST /api/v1/nfse/importar-xml`
- `POST /api/v1/nfse/importar-email` (anexos XML de `.eml`)
- `GET /api/v1/nfse/exportar.xlsx`
- `POST /api/v1/nfse/download-lote`
- `POST /api/v1/nfse/sincronizar-todas`
- `GET /api/v1/nfse/lotes/{lote_id}`
- `GET/POST /api/v1/nfse/{nfse_id}/eventos`
- `POST /api/v1/nfse/{nfse_id}/eventos/consultar-adn` (A1)
- `POST /api/v1/nfse/{nfse_id}/eventos/a3/importar` (resultado consultado pelo Bridge local)
- `GET/PUT /api/v1/nfse/{nfse_id}/lancamento`
- `GET /api/v1/nfse` agora aceita filtros opcionais de competência, direção, situação e pesquisa.

## Cuidados e limitações deliberadas

- A sincronização automática fica desativada por padrão e deve ser habilitada explicitamente em cada titular.
- A sincronização A1 usa a integração ADN que já existe no módulo. O A3 depende do OMEGA Bridge no computador com o cartão/token; a rotina do servidor registra necessidade de intervenção, não tenta usar o dispositivo físico no servidor.
- Alertas de numeração são apenas “possível lacuna”, nunca uma afirmação automática de nota faltante.
- Valores de ISS, IRRF, PIS, COFINS, CSLL e INSS são exibidos quando extraídos do XML. A extração depende dos campos presentes no XML; não substitui apuração tributária nem conferência profissional.
- Eventos informados pelo usuário ficam marcados como manuais. A consulta oficial utiliza `GET /NFSe/{ChaveAcesso}/Eventos` no endpoint de contribuintes do ADN com mTLS (A1) ou através do Bridge local (A3). Os resultados oficiais são armazenados com origem distinta e deduplicados pelo conteúdo consultado. Respostas sem conteúdo/sem eventos (HTTP 204/404) são exibidas como ausência de eventos, sem gerar registro inventado.
- O atalho do DANFSe abre a Consulta Pública nacional com a chave preenchida. A API antiga `GET /danfse/{chaveAcesso}` foi desativada em agosto de 2026; a geração/visualização atual é disponibilizada pela Consulta Pública oficial, que pode exigir verificação de segurança. Não se fabrica um PDF DANFSe localmente.
- O vínculo contábil fica gravado como `RASCUNHO`. Não faz lançamento automático em livro/razão porque o projeto não oferece, neste módulo, integração de lançamento definitivo implementada e confirmada.
- A importação por e-mail processa um arquivo `.eml` selecionado pelo usuário e seus anexos XML; não acessa uma caixa de entrada automaticamente nem armazena credenciais de e-mail.
- O DANFSe abre a Consulta Pública nacional com a chave da nota. Não é gerado um PDF sintético nem utilizado o endpoint antigo desativado em agosto de 2026.

## Testes realizados

- `py_compile` dos módulos Python alterados: passou.
- `pytest -q tests/test_nfse.py tests/test_health.py tests/test_api.py`: 38 passaram.
- `pytest -q` geral: 85 passaram e 1 falhou em `tests/test_brasilapi.py::test_brasilapi_resposta_json_invalida_gera_erro_controlado`; a falha está em `app/services/brasilapi.py`, fora deste escopo (a exceção `ValueError` de `response.json()` não é convertida em `BrasilAPIError`).
- Verificação de transpile/sintaxe TSX/TS via TypeScript `transpileModule`: ambos os arquivos alterados passaram sem erros sintáticos.
- Build completo Vite/React e verificação de tipos completos não puderam ser validados porque as dependências do frontend não estão disponíveis nesta sessão (`react`, `vite`, seus tipos etc.) e não foi possível completar a instalação. Execute `npm ci` e depois `npm run build` no ambiente de desenvolvimento antes de publicar.
