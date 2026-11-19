# Implementação da aba Certificados Digitais — A1/A3

Base: `OMEGA_RELEASE.zip` enviado em 07/10/2026.

## Implementado

### A1
- Upload PFX/P12 com limite de tamanho.
- Validação da senha e presença da chave privada.
- Extração de titular, CPF/CNPJ, emissor, série, thumbprint, algoritmo e validade.
- Bloqueio de certificado incompatível com o CNPJ da empresa.
- PFX armazenado fora do banco e criptografado com Fernet.
- Senha do PFX armazenada separadamente e criptografada.
- API nunca retorna senha nem caminho físico.
- Download A1 somente para ADMIN e com evento de auditoria.
- Substituição preserva o certificado anterior e registra evento.
- Teste do A1 revalida PFX, senha, chave privada e validade.

### A3
- Cadastro separado de A1.
- Meio CARTAO ou TOKEN.
- Não existe upload de PFX para A3.
- Não existe campo de PIN persistido.
- Não existe armazenamento de chave privada.
- Validação PJ x CNPJ.
- PF pode ser registrada como metadado, mas fica `NAO_VINCULADO` porque o projeto atual não possui uma relação formal de representação PF -> PJ.
- Detecção de certificado via OMEGA Bridge.
- Teste A3 pode realizar uma assinatura local de desafio através do Bridge; o PIN é enviado somente ao Bridge e não é armazenado.

### OMEGA Bridge
- Serviço local separado em `bridge/`.
- PC/SC/PySCard para leitores.
- PKCS#11 para certificados/chaves em token/cartão.
- HTTP protegido por Bearer token.
- WebSocket protegido por origem + subprotocol/token; token não vai na URL.
- PIN nunca é persistido.
- Assinatura suporta seleção automática de mecanismo RSA/ECDSA quando o middleware fornece o tipo da chave.

### Arquitetura
Foi criada a fachada `backend/app/services/certificado_service.py` para que futuros módulos, como NFS-e, não precisem conhecer PFX, storage, PC/SC, PKCS#11 ou PIN.

## Permissões
- Usuário autenticado: consulta metadados e solicita substituição.
- ADMIN: cadastra, substitui, testa, desativa e baixa A1.

O projeto atual não possui vínculo usuário -> empresa. Portanto, segregação fina por empresa para usuários comuns ainda deve ser implementada antes de permitir acesso operacional por empresa.

## Testes realizados
- `python -m compileall backend bridge` — PASSOU.
- Suíte existente + testes de Certificados: **34 passed**.
- Testes de API A1/A3, permissões, upload excedente, substituição e proteção de credenciais: PASSARAM.
- Bridge HTTP: health 200; sem token 401; origem proibida 403; token inválido 401; leitura de PC/SC retornou 503 corretamente porque o ambiente de auditoria não possui PySCard/PCSC.
- Teste com cartão/token A3 real: NÃO FOI POSSÍVEL TESTAR — motivo: hardware/middleware PKCS#11 não está disponível no ambiente de auditoria.
- Build completo do frontend: NÃO FOI POSSÍVEL TESTAR — motivo: o `node_modules` entregue/gerado no ambiente não contém todas as definições TypeScript necessárias e a instalação limpa ficou indisponível no ambiente. Os arquivos TS/TSX alterados foram verificados quanto à sintaxe com o compilador TypeScript 5.8.3.

## Configuração
Produção deve definir:
- `OMEGA_CERTIFICADO_MASTER_KEY`
- `OMEGA_CERTIFICADO_MAX_MB`
- `OMEGA_BRIDGE_TOKEN`
- `OMEGA_BRIDGE_ALLOWED_ORIGINS`
- `OMEGA_PKCS11_MODULE`
- `VITE_OMEGA_BRIDGE_URL`
- `VITE_OMEGA_BRIDGE_TOKEN`

Nunca versionar `.env` ou certificados reais.

## Correção pós-teste de integração — 07/10/2026

Foi identificado, em teste com banco legado, que `CREATE TABLE IF NOT EXISTS` não adicionava colunas novas à tabela `certificados` já existente. Isso causava erro no endpoint `GET /api/v1/certificados/resumo` quando o banco possuía a tabela antiga sem `apto_para_uso`.

A implementação foi corrigida para executar migrations compatíveis das colunas do módulo antes da criação dos índices. O cenário foi reproduzido com uma tabela legada e validado novamente.

Validação final do backend: **34 testes passando, 0 falhas**, em banco de teste limpo.
