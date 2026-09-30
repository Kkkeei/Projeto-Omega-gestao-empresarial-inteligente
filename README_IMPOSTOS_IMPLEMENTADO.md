# ÔMEGA — Impostos implementado

Implementação completa da especificação da aba Impostos, preservando os demais módulos do projeto.

## Incluído
- Visão geral das empresas, filtros por regime e situação, pesquisa e indicadores.
- Cadastro mestre de tributos, edição e inativação com preservação de histórico.
- Configuração de tributos por empresa com competência inicial/final e prevenção de sobreposição.
- Painel mensal por empresa e competência, com filtros por esfera.
- Registro mensal por guia, Credor ou Sem movimentação.
- Upload de PDF/JPG/PNG até 10 MB, extração de dados e OCR de PDF digitalizado/imagem.
- Conferência/edição das informações extraídas e mensagem padrão ao cliente.
- Documento, histórico, pagamento e comunicação vinculada à obrigação.
- Configuração persistente de notificações para cliente e contabilidade.
- Eventos de vencimento/antes do vencimento/guia registrada e alerta interno de vencidos.
- Relatório por empresa e período, prévia e PDF, com distinção entre Pendente, Credor, Sem movimentação e fora da vigência.

## Preservação
O pacote de código não substitui `backend/omega.db` nem `storage`.

## Validações executadas
- `python -m compileall -q backend/app backend/main.py`
- `pytest -q backend/tests/test_health.py backend/tests/test_api.py`
- Smoke test do módulo Impostos: cadastro, vínculo, competência, histórico, notificações idempotentes e relatório PDF.
- Verificação de rotas do módulo Impostos.

A compilação completa do frontend não foi executada porque a cópia de `node_modules` usada no ambiente de validação está incompleta (faltam definições de tipos). O código foi mantido sem alteração dos módulos não relacionados a Impostos.
