# Plataforma ÔMEGA

Plataforma de gestão empresarial com backend em FastAPI, frontend React/Vite/TypeScript, automações, gestão de empresas, certidões, documentação, faturamento, impostos e gerenciamento de Certificados Digitais A1/A3.

> Esta entrega prioriza estabilidade e preservação do que já funciona. O módulo NFS-e permanece como próxima etapa, após a validação do A3 em hardware real.

## Estado desta entrega

| Área | Situação |
|---|---|
| Backend FastAPI | Validado |
| Banco SQLite | Validado em ambiente de teste |
| Certificado A1 | Núcleo validado |
| Pessoa Física | Estrutura separada implementada |
| Certificado A3 | Cadastro e integração Bridge preparados |
| OMEGA A3 Bridge | Testes unitários/HTTP básicos validados |
| Hardware A3 real | Requer teste no Windows do cliente |
| Frontend | Código entregue; build depende de Node/npm |
| NFS-e | Próxima etapa |

## Testes realizados nesta entrega

Backend:

```bash
PYTHONPATH=backend OMEGA_ENV=test pytest -q backend/tests -ra
```

Resultado registrado nesta entrega:

```text
43 passed
```

Compilação:

```bash
python3 -m compileall -q backend bridge
```

Bridge:

```bash
PYTHONPATH=bridge pytest -q bridge/test_app.py -ra
```

Resultado:

```text
3 passed
```

O relatório completo está em:

```text
docs/AUDITORIA_FINAL_2026-10-08.md
```

## Estrutura

```text
OMEGA/
├── backend/                 API FastAPI, banco e serviços
├── frontend/                Interface React/Vite/TypeScript
├── bridge/                  OMEGA A3 Bridge local
├── docs/                    Documentação técnica e operacional
├── scripts/                 Scripts de QA e release
├── dados/                   Arquivos auxiliares do projeto
├── docker-compose.yml
└── LICENSE
```

## Backend

O backend utiliza:

- FastAPI
- SQLite
- JWT
- Pydantic
- Playwright
- pypdf
- cryptography
- automações de certidões

Instalação:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configuração:

```bash
cp .env.example .env
```

Para certificados A1, configure uma chave Fernet própria:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Coloque o resultado em `OMEGA_CERTIFICADO_MASTER_KEY`.

Em produção, essa chave é obrigatória.

Inicialização:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend

Requer Node.js e npm.

```bash
cd frontend
npm ci
npm run build
npm run dev
```

O arquivo `.env.example` define a URL do backend e a integração local com o Bridge.

## Certificados Digitais

### A1

Fluxo:

```text
PFX/P12
  -> validação da senha
  -> leitura X.509
  -> identificação do titular
  -> validação CNPJ/CPF
  -> criptografia
  -> armazenamento privado
```

O PFX e a senha não são retornados no payload normal da API.

### A3

O A3 não envia PFX nem chave privada para o servidor.

Fluxo:

```text
Cartão/token
      |
      v
Middleware do fabricante
      |
      v
PC/SC + PKCS#11
      |
      v
OMEGA A3 Bridge
      |
      v
ÔMEGA
```

O PIN só deve ser informado durante a operação criptográfica e não deve ser armazenado.

## OMEGA A3 Bridge no Windows

O pacote do Bridge está disponível dentro do frontend em:

```text
frontend/public/OMEGA_A3_BRIDGE_WINDOWS.zip
```

A instalação simplificada usa:

```text
bridge/INSTALAR_OMEGA_A3.bat
```

Após a instalação, o Bridge inicia automaticamente no logon do Windows.

Leia:

```text
docs/GUIA_A3_WINDOWS.md
```

## Banco e migrações

A aplicação possui inicialização idempotente e rotinas de migração para bancos legados.

Uma correção importante evita executar diretamente:

```sql
ALTER TABLE ... ADD COLUMN ... DEFAULT CURRENT_TIMESTAMP
```

O SQLite não aceita esse tipo de default não constante em `ADD COLUMN`. A migração adiciona a coluna de forma segura e preenche os valores existentes explicitamente.

Para ambientes de produção, recomenda-se futuramente migrar para migrations versionadas.

## QA rápido

Execute na raiz:

```bash
./scripts/qa_release.sh
```

Esse script valida:

1. compilação Python;
2. suíte backend;
3. suíte do Bridge.

O frontend deve ser validado separadamente com Node/npm:

```bash
cd frontend
npm ci
npm run build
```

## Segurança

Nunca versionar:

- `.env` real;
- banco operacional;
- certificados reais;
- PFX/P12 reais;
- senha de certificado;
- PIN de A3;
- chave Fernet de produção;
- tokens de produção.

O `.gitignore` deve permanecer ativo para esses arquivos.

## Limitações conhecidas

### Hardware A3

A assinatura com cartão/token físico precisa ser validada em um Windows que possua:

- leitor compatível;
- cartão ou token A3;
- middleware correto;
- biblioteca PKCS#11 correspondente.

O ambiente usado para a auditoria não possuía esse hardware, portanto esse teste não foi falsamente marcado como concluído.

### Frontend

O build não foi executado neste ambiente porque o comando `npm` não estava disponível. O código e as dependências estão presentes no projeto.

### Permissões por empresa

A estrutura atual de usuários não possui ainda uma ACL formal usuário-empresa. Antes de uma operação multiusuário com carteiras isoladas, deve ser implementada uma política explícita de vínculo e autorização por empresa.

## Próxima etapa: NFS-e

O NFS-e deve consumir uma camada de assinatura abstrata, sem conhecer detalhes de:

- PFX;
- armazenamento criptografado;
- PKCS#11;
- leitor;
- token;
- cartão;
- PIN;
- Bridge.

Arquitetura prevista:

```text
NFS-e
  |
  v
CertificateService / Signer
  |------------------|
  v                  v
A1Signer           A3Signer
  |                  |
PFX protegido      OMEGA Bridge
```

Isso evita duplicar a lógica de certificados dentro do módulo fiscal.

## Documentação

Principais documentos:

```text
docs/AUDITORIA_FINAL_2026-10-08.md
docs/GUIA_A3_WINDOWS.md
docs/CERTIFICADOS_A1_A3.md
docs/CERTIFICADOS_A1_A3_EXTENSOES_2026-10-07.md
docs/INSTALACAO_OMEGA_A3_WINDOWS.md
docs/ARQUITETURA.md
```

## Licença

MIT. Consulte `LICENSE`.
