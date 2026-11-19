# Auditoria técnica final — Plataforma ÔMEGA

Data: 08/10/2026
Base analisada: `OMEGA_RELEASE_A1_A3_VALID_A3_LEITOR_AUTOSTART.zip`

## 1. Objetivo

Esta auditoria verifica a base entregue para a Plataforma ÔMEGA, com atenção especial a:

- backend FastAPI;
- banco SQLite e inicialização/migrações;
- Certificados Digitais A1 e A3;
- Pessoas Físicas;
- OMEGA A3 Bridge;
- frontend React/Vite/TypeScript;
- segurança básica do armazenamento de certificados;
- testes automatizados;
- preparação para o próximo módulo NFS-e.

A regra de manutenção adotada foi: **preservar o que já funciona e corrigir somente o necessário para estabilizar a entrega**.

## 2. Testes executados nesta entrega

### Backend

```bash
PYTHONPATH=backend OMEGA_ENV=test pytest -q backend/tests -ra
```

Resultado desta execução:

```text
43 passed in 3.70s
```

### Compilação Python

```bash
python3 -m compileall -q backend bridge
```

Resultado: PASSOU.

### Bridge

```bash
PYTHONPATH=bridge pytest -q bridge/test_app.py -ra
```

Resultado:

```text
3 passed in 0.30s
```

## 3. O que foi confirmado como funcional

### Backend

- aplicação FastAPI possui suíte automatizada;
- banco de teste é separado do banco operacional;
- inicialização das tabelas é idempotente;
- há tratamento de migração para colunas de certificados em bancos legados;
- não é usado `DEFAULT CURRENT_TIMESTAMP` diretamente em `ALTER TABLE ADD COLUMN`;
- armazenamento A1 usa conteúdo criptografado;
- senha A1 é armazenada separadamente e criptografada;
- A3 não armazena PFX, chave privada ou PIN;
- eventos e usos de certificados possuem persistência própria.

### A1

O núcleo já possui validação de:

- PFX/P12;
- senha;
- presença da chave privada;
- validade temporal;
- identificação do titular;
- compatibilidade com CNPJ/CPF no fluxo correspondente;
- limite de upload;
- armazenamento criptografado.

### PF

Pessoas físicas possuem estrutura separada de empresas:

```text
pessoas_fisicas
certificados_pf
certificado_pf_eventos
certificado_pf_uso
```

Não é necessário criar empresa fictícia para um CPF.

### A3 / Bridge

A arquitetura atual possui:

```text
ÔMEGA Web
   |
   | HTTP localhost
   v
OMEGA A3 Bridge
   |
   +--> PC/SC
   |
   +--> PKCS#11
   |
   +--> cartão/token A3
```

O Bridge possui:

- `/health`;
- `/diagnostics`;
- `/readers`;
- `/certificates`;
- `/sign`;
- `/ws`.

O PIN é recebido apenas no processo de assinatura e não é persistido pelo Bridge.

## 4. Pontos que não podem ser declarados como testados

O ambiente desta auditoria não possui o hardware físico necessário. Portanto, não é correto afirmar que houve teste real de:

- cartão A3 físico;
- token USB A3;
- leitor PC/SC físico;
- middleware SafeSign/SafeNet instalado;
- DLL PKCS#11 real do usuário;
- PIN real;
- assinatura criptográfica em cartão físico;
- remoção/reinserção do cartão;
- bloqueio por PIN incorreto no dispositivo.

Esses testes precisam ser feitos em um Windows com o leitor e o certificado A3 reais.

## 5. Frontend

O código contém a tela de Certificados, fluxo PJ/PF, A1, A3, histórico, senha A1 e integração com o Bridge.

Não foi possível executar `npm install`/`npm run build` neste ambiente porque o executável `npm` não está instalado. Por isso, o build final do frontend deve ser executado em uma máquina com Node.js e npm.

## 6. Riscos e pontos de atenção

### 6.1 Isolamento multiempresa

A arquitetura de usuários da base atual não apresenta uma relação explícita `usuario -> empresa` equivalente a uma ACL por empresa. Esse ponto deve ser resolvido antes de disponibilizar o módulo em ambiente multiusuário com permissões por carteira de clientes.

Não foi aplicada uma alteração estrutural invasiva nesta entrega porque isso poderia quebrar os módulos existentes. A recomendação é criar uma política de acesso por empresa como etapa própria, com testes de autorização para todos os módulos que recebem `empresa_id`.

### 6.2 A3 físico

O Bridge está preparado para o fluxo local, mas o sucesso real depende do middleware e da DLL PKCS#11 fornecidos pelo fabricante/instalador do certificado.

### 6.3 WebSocket

O Bridge possui endpoint WebSocket próprio e autenticação por subprotocol. O fluxo atual de assinatura do frontend utiliza HTTP `/sign`; o WebSocket permanece disponível para evolução de eventos/comandos locais. Não deve ser tratado como canal de assinatura funcional obrigatório enquanto não houver teste de integração real.

### 6.4 Frontend

O build deve ser executado em CI ou máquina de desenvolvimento com Node/npm. Recomenda-se adicionar esse passo ao pipeline de release.

### 6.5 Migrações

A aplicação ainda usa migrações programáticas na inicialização do SQLite. Elas foram protegidas contra o problema conhecido de `ALTER TABLE ... DEFAULT CURRENT_TIMESTAMP`, mas a evolução de longo prazo deve migrar para versões explícitas de schema.

## 7. Classificação da entrega

```text
Backend                     PASSOU
Testes backend              43 passed
Compilação Python           PASSOU
Bridge unitário             3 passed
A1 núcleo                   PASSOU
A3 cadastro                 PASSOU PARCIALMENTE
A3 hardware físico         NÃO TESTADO
A3 assinatura física       NÃO TESTADA
Frontend build              NÃO EXECUTADO (npm indisponível)
Produção                    NÃO APROVADA sem testes de hardware e build
```

## 8. Próxima etapa recomendada

Antes de iniciar NFS-e:

1. instalar o Bridge em Windows;
2. conectar leitor + cartão A3;
3. instalar/validar middleware;
4. usar **Detectar dispositivo** no ÔMEGA;
5. selecionar o certificado encontrado;
6. cadastrar o A3;
7. executar **Testar acesso** e informar o PIN somente quando solicitado;
8. registrar o resultado;
9. executar o build do frontend;
10. só então consolidar a abstração de assinatura que será consumida pelo NFS-e.
