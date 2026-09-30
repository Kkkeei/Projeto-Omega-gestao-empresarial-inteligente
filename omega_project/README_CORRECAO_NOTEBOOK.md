# OMEGA — correção da cópia do notebook

Esta versão foi montada a partir do estado sincronizado do servidor (`origin/main`) e recebeu somente a integração do módulo **Impostos** e suas integrações mínimas.

## Correções

- Restaurado o módulo **Faturamento** para a versão do estado sincronizado do servidor, preservando a tela da empresa e o fluxo do Banco do Brasil.
- Restaurado o `banco_brasil_service.py` para a versão sincronizada do servidor.
- Restaurado `EmpresaFaturamentoPage.tsx`, `BancoBrasilDeclarationModal.tsx`, `Faturamento.css` e `FaturamentoEntryModal.tsx` para a versão sincronizada do servidor.
- Integrado o módulo **Impostos** ao menu, rotas, banco e API.
- Incluídas telas de visão geral, cadastro de tributos, configuração por empresa, registro mensal, guia/credor/sem movimentação, notificações e relatório.
- O banco do usuário **não está incluído** neste pacote.
- `storage`, `.venv`, `node_modules` e `.git` também não estão incluídos.

## Aplicação

Na pasta do projeto:

```bash
unzip -o OMEGA_NOTEBOOK_CORRIGIDO.zip
cd frontend && npm install
```

Suba o backend e o frontend normalmente.

**Não substitua `backend/omega.db` nem `storage`.**

## Validações executadas

- Backend Python: compilação dos módulos.
- Rotas Faturamento: carregadas.
- Rotas Impostos: carregadas (22 rotas).
- Testes do backend fora do conjunto legado de período do faturamento: 15/15 passaram.
- Parsing sintático dos 42 arquivos `.ts/.tsx`: 0 erros.
- Smoke test do Impostos: criação de empresa, tributo, vínculo, registro mensal e PDF do relatório.
