# ÔMEGA Frontend MVP

Frontend React + TypeScript + Vite para a Plataforma ÔMEGA de Gestão Empresarial.

## Requisitos
- Node.js
- Backend FastAPI do ÔMEGA rodando em `http://127.0.0.1:8000`

## Instalação
```bash
npm install
cp .env.example .env
npm run dev
```

Acesse `http://127.0.0.1:5173`.

## API
Por padrão:
`VITE_API_URL=http://127.0.0.1:8000`

O frontend usa apenas endpoints documentados do backend:
- `/health`
- `/api/v1/dashboard/resumo`
- `/api/v1/empresas`
- `/api/v1/empresas/{id}`
- `/api/v1/empresas/{id}/sync`
- `/api/v1/empresas/cnpj/{cnpj}/consulta`
- `/api/v1/certidoes`
- `/api/v1/pendencias`
- `/api/v1/automacoes/...`

## Estrutura
`src/modules` contém os módulos de negócio; `src/services/api` centraliza chamadas ao backend; `src/types` contém contratos TypeScript.
