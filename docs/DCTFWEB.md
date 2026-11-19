# Módulo DCTFWeb — fechamento interno

## Escopo
A aba DCTFWeb apresenta o acompanhamento de obrigações de tributos federais configurados na aba Impostos para empresas ativas enquadradas em Lucro Presumido ou Lucro Real. Os valores e estados são consultados no registro mensal existente; esta tela não mantém uma segunda fonte de valores.

## Endpoint
- `GET /api/v1/dctfweb/dashboard?ano=2026&mes=8` — retorna competência, tributos federais dinâmicos, empresas e indicadores agregados.

O endpoint exige a autenticação já aplicada às rotas da API.

## Estados
- `PENDENTE`: não há registro mensal final válido.
- `CREDOR`: apuração credora registrada.
- `SEM_MOVIMENTACAO`: ausência de movimentação informada explicitamente.
- `VALOR_INFORMADO`: registro mensal final com valor informado.
- `PAGO`: registro mensal marcado como pago.

O fechamento só fica liberado quando há pelo menos uma obrigação esperada e todas estão finalizadas. Uma competência sem obrigações permanece em estado vazio, sem liberação automática. Falhas de consulta retornam erro HTTP e não são interpretadas como conclusão.

## Limitação explícita
A ação “Conferir DCTFWeb” abre uma conferência interna dos dados da aba Impostos. Não existe transmissão oficial para a Receita Federal neste módulo. Antes de implementar transmissão, será necessária integração oficial suportada, autenticação/autorização adequada, validação do leiaute aplicável e confirmação verificável do protocolo de entrega.

## Validação
Esta alteração foi escrita pelo GitHub API. O build local do frontend, a suíte pytest e testes de integração com o banco ainda precisam ser executados em ambiente de desenvolvimento antes de considerar o módulo pronto para produção.
