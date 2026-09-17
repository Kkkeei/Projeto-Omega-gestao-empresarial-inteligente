# Aba Faturamento — ÔMEGA

Implementação do módulo de Faturamento sobre a estrutura existente da Plataforma ÔMEGA.

## Fluxo
- Lista todas as empresas ativas em ordem alfabética.
- Filtros por regime: Simples Nacional, Lucro Presumido e Lucro Real.
- Pesquisa por razão social, nome fantasia e CNPJ.
- Competência pendente = mês completo imediatamente anterior ao mês atual.
- Cada empresa mostra status pendente/informado e o último faturamento registrado.
- Tela interna da empresa para informar e editar competências.
- Geração de declaração dos últimos 12 meses completos, anual e personalizada.
- Histórico das declarações com data, tipo, período, total e usuário.
- Visualização e download dos PDFs.

## Banco
O backend cria automaticamente as tabelas `faturamentos` e `declaracoes_faturamento` sem apagar o banco existente.

## Dependência adicional
`reportlab` foi adicionado ao `backend/requirements.txt` para geração dos PDFs.

## Rotas principais
- `GET /api/v1/faturamento/empresas`
- `GET /api/v1/empresas/{empresa_id}/faturamento`
- `POST /api/v1/empresas/{empresa_id}/faturamento`
- `PUT /api/v1/faturamentos/{faturamento_id}`
- `POST /api/v1/empresas/{empresa_id}/declaracoes-faturamento/12-meses`
- `POST /api/v1/empresas/{empresa_id}/declaracoes-faturamento/anual`
- `POST /api/v1/empresas/{empresa_id}/declaracoes-faturamento/personalizada`
- `GET /api/v1/empresas/{empresa_id}/declaracoes-faturamento`
- `GET /api/v1/declaracoes-faturamento/{declaracao_id}/visualizar`
- `GET /api/v1/declaracoes-faturamento/{declaracao_id}/download`

A base do projeto foi preservada; o banco `omega.db` não acompanha o pacote.
