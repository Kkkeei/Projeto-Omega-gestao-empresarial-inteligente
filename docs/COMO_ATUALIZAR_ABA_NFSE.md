# Como aplicar a versão com a aba NFS-e

Este pacote contém a aba **NFS-e** integrada ao menu principal, a rota `/nfse`, a página React, o serviço frontend da API e as rotas/serviços backend da NFS-e. Também mantém a correção de extração de data e valor dos XMLs.

## Aplicação no Windows

1. Faça uma cópia de segurança da pasta atual do projeto.
2. Extraia este ZIP em uma pasta temporária.
3. Abra a pasta `OMEGA` extraída.
4. Copie o conteúdo de dentro de `OMEGA` para a pasta-raiz do projeto que você já utiliza, aceitando substituir os arquivos de código correspondentes.
5. **Preserve os arquivos e diretórios locais de produção**, especialmente `backend/.env`, `backend/omega.db` e `backend/storage` (ou o diretório de storage configurado no `.env`). Este ZIP não inclui esses dados operacionais.
6. Reinicie o backend FastAPI.
7. Na pasta `frontend`, instale as dependências com `npm ci` se necessário e execute `npm run dev` ou o processo de build/deploy já usado no seu ambiente.
8. Atualize o navegador. A aba **NFS-e** deve aparecer no menu lateral imediatamente abaixo de **Certificados**. A rota direta é `/nfse`.

## Se a aba ainda não aparecer

Confirme se os arquivos abaixo foram atualizados na pasta do projeto que o Vite realmente está executando:

- `frontend/src/components/layout/Layout.tsx` — inclui a entrada de menu `/nfse`.
- `frontend/src/app/App.tsx` — registra a rota `/nfse` e importa `NfsePage`.
- `frontend/src/modules/nfse/NfsePage.tsx` — página NFS-e.
- `frontend/src/services/api/nfse.ts` — chamadas HTTP da NFS-e.
- `backend/app/api/v1/routes.py` — registra o router NFS-e.
- `backend/app/modules/nfse/routes.py` e `service.py` — endpoints e regras de consulta/importação.

Se o servidor estiver executando uma pasta diferente, alterar outra cópia do código não muda a aplicação aberta no navegador. Confirme a pasta em que você executa `npm run dev` e o terminal de onde o backend foi iniciado.

## Escopo funcional

A aba atual é voltada à consulta/importação de documentos distribuídos pelo ADN com certificado A1/A3. Isso não significa que a emissão, o cancelamento e a substituição municipal de NFS-e estejam implementados para todos os provedores.
