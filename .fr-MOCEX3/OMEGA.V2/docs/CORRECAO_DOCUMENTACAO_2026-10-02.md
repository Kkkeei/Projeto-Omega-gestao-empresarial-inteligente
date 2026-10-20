# Correção da Aba Documentação — 2026-10-02

## Problema

A versão enviada para revisão havia regredido a tela de documentação para uma navegação por abas horizontais. Isso deixou a representação das pastas visualmente grande e também eliminou a experiência de explorador necessária para trabalhar com subpastas.

## Correção

A tela da empresa foi restaurada para o padrão compacto de explorador de arquivos, com:

- árvore lateral de pastas e subpastas;
- seleção da pasta atual sem cards gigantes;
- breadcrumb de navegação;
- voltar, subir, raiz e atualizar;
- pesquisa no nível atual;
- Nova pasta e Subpasta separados;
- upload somente quando existe uma pasta aberta;
- edição e arquivamento da pasta atual;
- documentos e versões no painel principal.

## Backend

A listagem de categorias voltou a retornar a árvore completa de pastas ativas, incluindo `subpastas_count`.

A edição passou a respeitar o mesmo nível hierárquico da pasta, permitindo alterar pastas filhas sem quebrar a estrutura.

O arquivamento de uma pasta continua recursivo, preservando o histórico lógico dos itens.

## Validação

O teste automatizado específico da documentação foi executado com sucesso:

`1 passed`

O código TSX da aba Documentação também foi validado por transpile sintático com o TypeScript disponível no ambiente.

O build completo do frontend não pôde ser concluído neste ambiente porque as dependências npm do projeto não estavam disponíveis integralmente e o ambiente não conseguiu completar a instalação via registry. Nenhum `node_modules` é incluído no ZIP final.

## Regra preservada

O banco operacional `backend/omega.db` não faz parte do pacote e não é substituído pela correção.
