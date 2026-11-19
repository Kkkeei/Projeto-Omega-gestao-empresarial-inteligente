# Correção do carregamento de certificados na NFS-e

## O que mudou

- O contexto NFS-e continua selecionando automaticamente um certificado ativo e apto da entidade escolhida (PF ou PJ).
- A leitura da validade aceita ISO 8601 e formatos legados comuns (`DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY/MM/DD`, `YYYYMMDD`). Datas sem horário são consideradas válidas até o final do dia.
- A seleção não exige `storage_ref` no objeto público do certificado. O repositório de certificados remove esse campo deliberadamente para não expô-lo; a disponibilidade real do PFX é validada pela fachada na operação mTLS.
- Para A3 continua obrigatória a presença de thumbprint SHA-256 para associar o cartão ao cadastro.
- Quando nenhum certificado pode ser usado, a API devolve metadados de diagnóstico sem segredos, incluindo os certificados cadastrados e o motivo pelo qual cada um não pode ser selecionado. A tela NFS-e exibe esses motivos em vez de indicar apenas que nenhum certificado existe.

## Arquivos alterados

- `backend/app/modules/nfse/service.py`
- `backend/tests/test_nfse.py`
- `frontend/src/services/api/nfse.ts`
- `frontend/src/modules/nfse/NfsePage.tsx`
- `frontend/src/styles.css`

## Validação executada

- Backend: `79 passed`.
- OMEGA Bridge: `3 passed`.
- `python -m compileall -q backend bridge`: passou.
- Build frontend completo: não executado, pois as dependências npm não estão instaladas integralmente neste ambiente.

## Depois de atualizar

Preserve o `backend/.env`, `backend/omega.db` e o diretório `storage` existentes. Copie os arquivos do pacote para a raiz do projeto atual, reinicie o backend e o frontend, abra NFS-e, selecione PF/PJ e o titular.

Se o certificado ainda não for selecionado, a tela agora deve mostrar os certificados encontrados e o motivo (status, aptidão, validade ou thumbprint A3). Use esse motivo para corrigir o cadastro na aba Certificados; não altere o banco manualmente.
