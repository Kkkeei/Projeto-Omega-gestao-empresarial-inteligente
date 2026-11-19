# Certificados Digitais A1/A3 — ÔMEGA

## Princípios

- A1: PFX/P12 é validado e armazenado criptografado fora do banco; senha também é criptografada e nunca retornada.
- A3: nenhuma chave privada, PFX ou PIN é armazenado no backend.
- A3 é identificado por cartão/token e deve ser utilizado pelo OMEGA Bridge.
- O NFS-e futuro deve consumir `CertificadoService`, sem conhecer storage, PFX, PC/SC, PKCS#11 ou PIN.

## Variáveis

`OMEGA_CERTIFICADO_MASTER_KEY` é uma chave Fernet independente do banco. Em produção é obrigatória.

`OMEGA_CERTIFICADO_MAX_MB` controla o limite de upload A1.

## Bridge

O Bridge é opcional para A1 e obrigatório para A3 real. Ele usa PC/SC para leitores e PKCS#11 para operações criptográficas.

O PIN existe somente na chamada de assinatura e não é persistido.

## Permissões

- Usuário autenticado: consulta metadados e solicita substituição.
- ADMIN: cadastra, substitui, testa, desativa e baixa A1.

O projeto atual ainda não possui relação usuário -> empresa; por isso a segregação por empresa de usuários comuns deve ser implementada antes de permitir que usuários comuns tenham acesso operacional por empresa.
