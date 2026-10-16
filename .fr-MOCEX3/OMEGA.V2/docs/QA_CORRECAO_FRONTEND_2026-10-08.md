# QA — Correção do erro JSX do módulo de Certificados

## Erro reproduzido

O log do Windows/Vite apontava para `frontend/src/modules/certificados/CertificadosPage.tsx`, linha 227, com:

`Unexpected token, expected ":" (227:13)`

A origem estava na expressão condicional que inicia o bloco de detalhes do certificado. O código usava `selected ? <>...</>` sem o ramo `:` de uma expressão ternária.

## Correção

A expressão foi alterada para renderização condicional por `&&`:

`{selected&&<>...</>}`

Não foram alteradas regras de negócio nem módulos não relacionados.

## Validação

- Testes backend: **43 passed** (`python -m pytest -q`).
- O build Vite não foi executado neste ambiente porque o pacote `node_modules`/Vite não está disponível na cópia de trabalho e o `npm` local deste ambiente não está funcional.
- O log fornecido pelo servidor Windows confirma que o erro original é de parsing JSX/Babel exatamente nesse ponto.

## Validação no Windows

Na pasta `frontend` do projeto corrigido:

```powershell
npm run dev
```

ou, para validação de produção:

```powershell
npm run build
```

O erro `Unexpected token, expected ":" (227:13)` não deve mais ocorrer após a correção.
