# Operação no Windows

## Banco
Preserve `backend/omega.db`. O ZIP de atualização não inclui banco SQLite.

## Backend
Na raiz do projeto, com `.venv` na raiz:

```powershell
cd C:\Users\Administrador.SRV\Desktop\OMEGA
.\.venv\Scripts\Activate.ps1
cd .\backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Frontend
```powershell
cd C:\Users\Administrador.SRV\Desktop\OMEGA\frontend
npm install
npm run dev -- --host 0.0.0.0
```

## Rede
Frontend: `http://192.168.100.3:5173`
API: `http://192.168.100.3:8000`

O backend não sincroniza a BrasilAPI no startup por padrão. Isso evita `429 Too Many Requests`. Para atualização cadastral, use a rota de sincronização de forma controlada.
