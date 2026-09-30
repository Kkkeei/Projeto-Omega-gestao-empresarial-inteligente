# Banco SQLite do ÔMEGA

## Importante
Nunca substitua `backend/omega.db` enquanto o Uvicorn/FastAPI estiver rodando.
Pare o backend antes de atualizar o projeto ou restaurar um banco.

O pacote de desenvolvimento não deve distribuir uma cópia de `omega.db` sobre um
banco existente. Em instalações novas, `criar_tabelas()` cria o banco vazio e
insere os tributos mestre iniciais.

## Diagnóstico

No diretório `backend`:

```bash
python scripts/reparar_banco.py
```

Se o banco estiver íntegro, nada será alterado.

Se estiver corrompido, o script:

1. preserva `omega.db` e os sidecars `-wal`/`-shm`;
2. usa o recurso `.recover` do SQLite;
3. valida o banco recuperado;
4. só então substitui o banco danificado;
5. mantém o original arquivado.

Se o comando `sqlite3` não existir, instale o SQLite antes de executar o reparo.
