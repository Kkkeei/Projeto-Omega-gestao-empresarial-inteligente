# Correção — Aba Documentação

Corrigido o erro de compilação JSX em `frontend/src/modules/documentacao/EmpresaDocumentacaoPage.tsx`.

A página foi reestruturada com JSX explícito e fragmentos condicionais, mantendo:
- pastas/categorias por tipo de documento;
- upload;
- visualização e download;
- histórico de versões;
- criação de novas pastas e subpastas;
- arquivamento lógico de categoria.

O ZIP não contém `backend/omega.db` nem `node_modules`.

## Ajuste da tela interna da empresa - 2026-09-16

A área `EmpresaDocumentacaoPage.tsx` foi reorganizada para funcionar como um explorador de arquivos:

- as pastas `Pessoal (Sócio)`, `Societário` e `IRPF` funcionam como cabeçalhos expansíveis;
- ao clicar no cabeçalho, os documentos da respectiva pasta aparecem imediatamente abaixo;
- o botão `Adicionar documento` fica dentro da seção aberta;
- histórico, visualização, download e nova versão permanecem nas ações de cada documento;
- não há mais uma página separada apenas para listar as três pastas.

A interface continua usando as entidades de documentação já existentes.
