# Aba Faturamento — ÔMEGA

Implementação do módulo de Faturamento sobre a estrutura existente da Plataforma ÔMEGA.

## Visual e fluxo atualizado
- Painel inicial com quatro indicadores: total de empresas, faturamentos pendentes, faturamentos informados e total da competência de controle.
- Cards de regime: Todas, Simples Nacional, Lucro Presumido e Lucro Real.
- Pesquisa por razão social, nome fantasia, CNPJ ou NIRE.
- Seletor de competência de controle para consultar qualquer competência recente.
- Lista das empresas em tabela compacta, com status, competência, último faturamento e ações rápidas.
- Ações: informar faturamento, gerar declaração e visualizar a empresa.
- Tela interna com cinco indicadores anuais: meses informados, total do ano, média mensal, último e primeiro faturamento.
- Grade mensal Janeiro a Dezembro com edição por competência.
- Informar faturamento individual em modal.
- Informar vários meses em modal com preenchimento em lote/upsert.
- Observação permanente da empresa no próprio módulo de Faturamento.
- Declarações: últimos 12 meses, anual e personalizada.
- Histórico de declarações compacto, com visualização e download.
- Modal global de geração de declaração quando acionado pela tela geral.
- Mensagens de sucesso discretas em toast.

## Regra da competência de controle
Por padrão, a competência é o mês completo imediatamente anterior ao mês atual. O usuário também pode trocar o mês/ano de controle na tela geral.

## Banco
O backend cria automaticamente as tabelas `faturamentos` e `declaracoes_faturamento` sem apagar o banco existente.

## Dependência adicional
`reportlab` é usado para geração dos PDFs.

## Declaração de faturamento
O PDF segue o padrão do documento de referência enviado para o Grupo ÔMEGA, com logo, texto de declaração, tabela mensal, local/data, identificação do contador, assinatura e rodapé do escritório.

## Rotas principais
- `GET /api/v1/faturamento/empresas`
- `GET /api/v1/empresas/{empresa_id}/faturamento`
- `POST /api/v1/empresas/{empresa_id}/faturamento`
- `POST /api/v1/empresas/{empresa_id}/faturamento/lote`
- `PATCH /api/v1/empresas/{empresa_id}/faturamento/observacao`
- `PUT /api/v1/faturamentos/{faturamento_id}`
- `POST /api/v1/empresas/{empresa_id}/declaracoes-faturamento/12-meses`
- `POST /api/v1/empresas/{empresa_id}/declaracoes-faturamento/anual`
- `POST /api/v1/empresas/{empresa_id}/declaracoes-faturamento/personalizada`
- `GET /api/v1/empresas/{empresa_id}/declaracoes-faturamento`
- `GET /api/v1/declaracoes-faturamento/{declaracao_id}/visualizar`
- `GET /api/v1/declaracoes-faturamento/{declaracao_id}/download`

A base do projeto foi preservada; o banco `omega.db` não acompanha o pacote.

## Correções recentes
- O botão "Informar faturamento" da lista abre o formulário em modal, sem navegar para a tela detalhada.
- A ação de informar permite criar ou editar diretamente a competência selecionada.
- O status anual identifica "Pendente em <mês>" quando há somente um mês pendente e "Pendente vários meses" quando há mais de um mês encerrado sem lançamento.
- Requisições do frontend têm limite de 20 segundos para evitar carregamento indefinido quando o backend não responde.
