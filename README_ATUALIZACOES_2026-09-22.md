# ÔMEGA — Projeto completo atualizado

Esta distribuição consolida as implementações realizadas no projeto ÔMEGA nesta etapa.

## Incluído
- Estrutura completa do projeto (backend + frontend + documentação técnica).
- Certidões e demais módulos existentes na base do projeto.
- Faturamento com novo layout, indicadores, filtros por regime, competência, lista de empresas, status de pendência e fluxo de informação.
- Faturamento com cartão/linha de empresa clicável.
- Formulário de informação de faturamento com data e periodicidade.
- Declarações de faturamento: 12 meses, anual e personalizada.
- Service de geração de declaração baseado no template PDF fornecido, preservando identidade visual, logo, assinatura e rodapé, alterando os dados dinâmicos.
- Documentação com pastas padrão, criação de novas pastas, edição, arquivamento e layout em abas.
- Suporte às alterações de API necessárias para pastas editáveis.

## Intencionalmente não incluído
- `omega.db`, `omega.db-wal` e `omega.db-shm`.
- `node_modules/` e outros artefatos gerados.

O banco deve ser preservado no ambiente de execução.


Correção adicional: visualização e download de declarações do Faturamento agora usam fetch autenticado com Bearer token e Blob, em vez de abrir diretamente a rota protegida.
