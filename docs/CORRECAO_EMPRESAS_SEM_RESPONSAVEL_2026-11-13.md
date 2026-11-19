# Correção — empresas sem responsável no Contábil

Data: 13/11/2026

## Problema

O dashboard (`GET /api/v1/contabil/dashboard`) aplicava, para usuários não administradores, o filtro `responsavel_id = usuário_logado`. Empresas cadastradas em Empresas, mas ainda sem linha ativa em `contabil_atribuicoes`, eram removidas da resposta. A tela Contábil exibia zero empresas embora o cadastro principal apresentasse empresas ativas.

O mesmo filtro estava presente no painel de Lançamentos e Conferências. Além disso, a validação de acesso ao detalhe exigia atribuição explícita, o que impediria abrir uma empresa desatribuída mesmo que ela fosse listada.

## Regra aplicada

- Empresa ativa sem responsável: aparece na carteira compartilhada dos usuários autenticados e pode ser acessada até receber uma atribuição.
- Empresa com atribuição ativa ao usuário: aparece e pode ser acessada por esse responsável.
- Empresa com atribuição ativa a outra pessoa: não aparece e não pode ser acessada pelo usuário comum.
- Administradores continuam vendo todas as empresas e administrando as atribuições.

A regra foi alinhada em `listar_dashboard`, `listar_painel_lancamentos_conferencias`, `obter_painel_empresa_lancamentos` e nas validações de operações de movimentações. Não há alteração no schema ou nos dados do banco.

## Validação

- `tests/test_contabil_lancamentos_conferencias.py`: 14 aprovados.
- `python -m compileall -q backend/app backend/tests`: sem erros.
- Suíte completa: 99 aprovados e 6 falhas preexistentes em funções NFS-e ausentes (`painel`, `importar_xml_manual`, `importar_email_eml`, `_request_a1_url` e `importar_eventos_a3`).
- Build integral do frontend não executado; a alteração é exclusivamente no backend e documentação.
