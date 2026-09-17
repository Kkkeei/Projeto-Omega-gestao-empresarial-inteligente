# Exclusão de documentos e pastas — Aba Documentação

Implementado:
- botão de excluir documento em cada linha;
- botão de excluir pasta no card da pasta;
- confirmação obrigatória antes da exclusão;
- exclusão lógica (arquivamento), preservando histórico físico/auditoria;
- ao excluir uma pasta, os documentos ativos daquela pasta também são arquivados;
- mensagens e modal de confirmação no frontend.

## Rotas
- DELETE /api/v1/documentacao/documentos/{documento_id}
- DELETE /api/v1/documentacao/categorias/{categoria_id}
