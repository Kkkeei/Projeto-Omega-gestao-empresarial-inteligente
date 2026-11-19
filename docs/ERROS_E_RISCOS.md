# Erros encontrados e riscos potenciais

Este documento separa problemas confirmados em execução de riscos que ainda dependem de ambiente externo.

## Confirmados e tratados na base

| Item | Severidade | Situação |
|---|---|---|
| Migração SQLite com `DEFAULT CURRENT_TIMESTAMP` em `ADD COLUMN` | Crítica | Tratada |
| Limite de upload A1 | Alta | Implementado |
| Dependência `cryptography` no backend | Alta | Declarada |
| Dependência `websockets` no Bridge | Alta | Declarada |
| Download/senha A1 fora do payload normal | Alta | Implementado |
| Armazenamento de PFX A1 criptografado | Alta | Implementado |
| PIN A3 persistido | Crítica | Não é persistido |
| Chave privada A3 enviada ao backend | Crítica | Não é enviada |
| PF misturado com empresa fictícia | Alta | Estrutura PF separada |
| Falta de suporte visual a TOKEN no A3 | Média | Fluxo possui CARTAO/TOKEN |
| Download de A1 para certificados arquivados | Média | Implementado |

## Riscos que exigem validação adicional

### 1. Hardware A3

Sem cartão/token e leitor reais não é possível provar compatibilidade com o middleware instalado na máquina do cliente.

### 2. PKCS#11

O caminho da DLL varia conforme fabricante, arquitetura 32/64 bits e versão do middleware. O instalador tenta caminhos conhecidos, mas mantém diagnóstico para configuração específica.

### 3. PIN incorreto/bloqueio

O comportamento final depende do dispositivo e middleware. Deve ser testado com política segura e sem utilizar um cartão de produção em testes destrutivos.

### 4. Remoção do cartão durante assinatura

Deve ser testada no Windows real para garantir que o Bridge retorna erro limpo e libera a sessão.

### 5. Frontend build

A máquina desta auditoria não tinha npm. Portanto, TypeScript/Vite precisa ser compilado em ambiente com Node.js.

### 6. Navegador Playwright

A suíte backend pode passar mesmo que o Chromium do Playwright não esteja instalado. O E2E do navegador é uma etapa independente.

### 7. Docker

Docker não é requisito para os testes locais desta entrega e não foi usado na auditoria. Deve ser validado em ambiente que tenha Docker instalado antes de publicar uma imagem de produção.

### 8. Multiempresa

O sistema precisa de uma ACL explícita de usuário por empresa se diferentes usuários tiverem carteiras distintas. Essa é uma evolução de autorização, não uma simples correção de certificado.

### 9. Concorrência de substituição

Duas requisições simultâneas de cadastro do mesmo tipo podem exigir uma regra transacional/índice parcial quando o volume crescer. Hoje a aplicação faz a substituição em transação SQLite, mas essa regra merece teste concorrente antes de operação de alta escala.

### 10. Expiração automática

O status persistido e a validade do certificado devem ser reconciliados no momento de uso. Não se deve confiar apenas em um status antigo gravado no banco.

### 11. Rotação da chave mestre A1

A troca de `OMEGA_CERTIFICADO_MASTER_KEY` invalida a descriptografia dos certificados antigos se não houver uma estratégia de rotação. Produção precisa de procedimento de backup/rotação antes de trocar essa chave.

### 12. Backup

Backup do banco sem backup do storage criptografado de certificados não permite recuperar certificados A1. Banco e storage precisam ser tratados como conjunto.

### 13. Exposição de segredo em logs

O PIN não deve aparecer em logs. O mesmo cuidado vale para senha A1, token do Bridge e `OMEGA_CERTIFICADO_MASTER_KEY`.

### 14. CORS

A origem do frontend precisa estar explicitamente configurada. Não abrir CORS para `*` em produção.

### 15. NFS-e

Não iniciar emissão real antes de consolidar uma abstração de assinatura. O módulo fiscal não deve implementar diretamente PFX, PKCS#11 ou PIN.
