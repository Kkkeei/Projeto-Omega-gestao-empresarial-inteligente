# Release — Certificados Digitais A1/A3

## Escopo

Esta release consolida a implementação da aba **Certificados Digitais** do Projeto ÔMEGA, limitada aos tipos A1 e A3.

## Correções críticas

- Corrigida a migration de SQLite para bancos existentes.
- `ALTER TABLE ... ADD COLUMN` não utiliza mais `DEFAULT CURRENT_TIMESTAMP` em colunas adicionadas a tabelas legadas.
- Datas de registros legados são preenchidas explicitamente após a adição das colunas.
- Corrigida a referência inexistente `tipo_sem_default` na migration de certificados.
- A migration de certificados, eventos e usos é idempotente.
- O resumo de certificados foi protegido contra o erro `no such column: apto_para_uso`.
- A interface passou a considerar A1 e A3 simultaneamente na mesma empresa, sem perder um certificado por causa de um `Map` com uma única entrada.
- A suíte de testes passou a remover o banco de teste anterior antes da execução, evitando falso positivo/falso negativo por estado persistente.

## Validação executada

### Backend

- `python -m compileall backend bridge` — OK
- `python -m pytest -q` — **36 passed, 0 failed**
- Inicialização real com Uvicorn — OK
- Migração de banco legado de certificados — OK
- Execução repetida da migration — OK
- Endpoint de resumo após migration — OK

### Frontend

O código alterado foi validado sintaticamente. A build completa depende da instalação das dependências NPM do projeto. O ambiente de validação não conseguiu completar `npm ci` por indisponibilidade/timeout do acesso ao registry, portanto esta release **não declara uma build Vite completa como validada**.

Para validar localmente:

```bash
cd frontend
npm ci
npm run build
```

## A3 / hardware

O OMEGA Bridge foi incluído para integração local com leitor/cartão/token e PKCS#11. A assinatura com hardware criptográfico físico depende do middleware e do dispositivo instalados na máquina do usuário e não pôde ser executada neste ambiente de validação.

## Segurança

- A1: PFX é armazenado cifrado fora do banco.
- Senha do A1 é armazenada cifrada separadamente.
- A3: chave privada e PIN não são armazenados pelo backend.
- Download do A1 é restrito a ADMIN.
- Ações administrativas são protegidas por autenticação/perfil.
