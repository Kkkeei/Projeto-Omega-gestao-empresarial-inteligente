# OMEGA A3 Bridge — instalação no Windows

## Objetivo

O usuário final não precisa abrir terminal nem executar comandos para usar A3. A instalação é feita uma única vez pelo pacote `OMEGA_A3_BRIDGE_WINDOWS.zip`.

## Instalação

1. Baixe `OMEGA_A3_BRIDGE_WINDOWS.zip` pela tela de Certificados.
2. Extraia o ZIP.
3. Dê duplo clique em `INSTALAR_OMEGA_A3.bat`.
4. O instalador cria o componente em `%LOCALAPPDATA%\OMEGA\A3Bridge`.
5. Cria a tarefa agendada `OMEGA A3 Bridge` para iniciar no logon.
6. Detecta automaticamente `aetpkss1.dll` (SafeSign) ou `eTPKCS11.dll` (SafeNet), quando presentes.

Depois disso, o usuário não precisa executar comandos novamente.

## Uso no ÔMEGA

Abra **Certificados → A3 → Detectar dispositivo**.

O Bridge consulta PC/SC e PKCS#11 no computador local. A chave privada permanece no cartão/token. O PIN é usado apenas durante a assinatura e não é armazenado.

## Remoção

Execute `DESINSTALAR_OMEGA_A3.bat`.

## Requisitos

- Windows;
- Python 3.11+ instalado no computador do Bridge;
- driver/middleware do leitor/cartão A3;
- cartão/token conectado para detectar o certificado.

## Driver da leitora e middleware do cartão

O **driver da leitora/cartão não é o OMEGA Bridge**. O driver depende do modelo da leitora e o middleware depende do fabricante/mídia do A3.

No Windows, o usuário deve instalar:

1. **Driver da leitora** — faz o Windows reconhecer a leitora USB/Smart Card.
2. **Middleware/gerenciador criptográfico** — permite que o Windows e o Bridge acessem o cartão/token.
3. **OMEGA A3 Bridge** — faz a comunicação local entre o navegador e o A3.

A página oficial de downloads da Certisign reúne drivers de leitoras e opções de SafeSign/SafeNet:

https://suporte.certisign.com.br/duvidas-suporte/downloads/leitoras

Não é correto instalar um driver genérico sem identificar a leitora e a mídia. A própria Certisign orienta instalar os dois componentes (leitora e cartão/middleware), e a Serasa informa, por exemplo, que cartões Gemalto/Thales usam SafeNet e cartões G&D usam SafeSign.
