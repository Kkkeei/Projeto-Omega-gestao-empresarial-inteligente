# Correção — Visualização de Declaração de Faturamento

## Problema
A rota `/api/v1/declaracoes-faturamento/{id}/visualizar` é protegida por autenticação Bearer. O frontend estava abrindo essa URL diretamente com `window.open()`.

Uma nova aba do navegador não envia o header `Authorization: Bearer ...`, então o FastAPI retornava:

```json
{"detail":"Autenticação necessária."}
```

## Correção
A visualização agora:
1. abre uma aba em branco no contexto do clique do usuário;
2. busca o PDF com `fetch()` e o token armazenado em `localStorage`;
3. cria um `Blob URL` autenticado;
4. direciona a aba para o Blob URL.

O download também usa o mesmo fluxo autenticado.

## Arquivos alterados
- `frontend/src/services/api/faturamento.ts`
- `frontend/src/modules/faturamento/FaturamentoPage.tsx`
- `frontend/src/modules/faturamento/EmpresaFaturamentoPage.tsx`

## Validação
- Backend: `python3 -m compileall` concluído sem erros.
- O build TypeScript não foi concluído neste ambiente porque faltam dependências `@types/*` no `node_modules` disponível. No seu ambiente, execute `npm install` dentro de `frontend` antes de `npm run build`.

## Banco
Nenhum arquivo `omega.db`, `omega.db-wal` ou `omega.db-shm` foi incluído nesta entrega.
