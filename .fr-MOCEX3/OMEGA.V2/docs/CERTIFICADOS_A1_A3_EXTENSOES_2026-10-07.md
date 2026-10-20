# Certificados Digitais A1/A3 — extensões de gestão de credenciais

## Alterações implementadas

- Aba dedicada à senha do certificado A1 dentro do painel de detalhes.
- Recuperação administrativa da senha A1 armazenada de forma criptografada.
- Download da senha A1 em arquivo TXT.
- A senha continua fora dos payloads normais dos certificados.
- A recuperação funciona também para certificados A1 inativos/substituídos e vencidos, desde que a credencial criptografada ainda exista no armazenamento.
- PIN de A3 continua sem armazenamento e, portanto, não pode ser recuperado.
- Alternância visual entre certificados de Pessoa Jurídica (PJ) e Pessoa Física (PF).
- Painel de histórico passa a apresentar explicitamente todos os certificados da empresa, inclusive os registros antigos/substituídos.
- Painel lateral de detalhes ampliado em telas grandes.
- Card de ações transformado em bloco sticky/flutuante durante a rolagem do detalhe.

## Segurança

A recuperação de senha é restrita ao perfil ADMIN. Cada recuperação gera evento de auditoria `SENHA_ACESSADA`.

O A3 permanece dependente do OMEGA Bridge: chave privada e PIN continuam no cartão/token e não são armazenados pelo backend.

## Compatibilidade

Nenhum campo existente foi removido e o comportamento anterior de cadastro, substituição, teste, download do A1, desativação e histórico foi preservado.
