# ÔMEGA — Certidões e alteração de regime

Alterações desta versão:

- Central de Certidões organizada no padrão da Aba Documentação: seleção por cards no topo e apenas o conteúdo do tipo selecionado no painel inferior.
- O painel selecionado mostra situação, emissão, validade, número e ações de PDF.
- Histórico e PDFs continuam disponíveis abaixo.
- Alteração do regime tributário deixou de usar `window.prompt` e agora usa um formulário modal rápido e organizado.
- O formulário mostra regime atual, novo regime, mês/ano de início e observação opcional.
- A alteração continua usando o endpoint existente e registra histórico.

Observação: o banco `omega.db` não faz parte deste pacote.
