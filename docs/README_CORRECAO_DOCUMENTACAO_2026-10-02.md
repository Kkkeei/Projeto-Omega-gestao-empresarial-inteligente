# Correção da Documentação — 02/10/2026

A interface de Documentação foi restaurada para a implementação anterior com explorador hierárquico (árvore lateral, breadcrumb, navegação e lista compacta), sem redesenho do módulo.

## Correções

- criação de pasta na raiz;
- criação de subpasta dentro da pasta atualmente aberta;
- botão `Subpasta` na raiz cria na própria raiz;
- árvore completa de pastas e subpastas retornada pela API;
- abertura e navegação em qualquer nível;
- edição de pastas e subpastas;
- validação de nomes duplicados no mesmo nível;
- criação/garantia do diretório físico por ID da categoria;
- arquivamento recursivo de pasta, subpastas e documentos ativos;
- upload e novas versões usando o diretório estável da categoria;
- preservação do histórico de auditoria.

## Validação

- `py_compile` do módulo de Documentação: OK
- teste funcional de raiz → subpasta → segundo nível → edição → arquivamento recursivo: OK
- `omega.db`, `.env`, `storage/`, `node_modules/`, `.venv/` e `.git/` não fazem parte do pacote de entrega.
