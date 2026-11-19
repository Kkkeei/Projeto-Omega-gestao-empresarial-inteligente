# OMEGA A3 Bridge — instalação no Windows

## Para que serve

O OMEGA A3 Bridge é o componente local que permite ao navegador conversar com o leitor/cartão/token A3 do computador.

Ele não substitui o certificado e não guarda a chave privada.

## Instalação

1. Abra o OMEGA.
2. Entre em **Certificados**.
3. Abra o fluxo A3.
4. Clique em **Instalar componente A3**.
5. Extraia `OMEGA_A3_BRIDGE_WINDOWS.zip`.
6. Execute `INSTALAR_OMEGA_A3.bat`.
7. O instalador cria o serviço local e configura inicialização automática no logon.

O Bridge fica em:

```text
http://127.0.0.1:8765
```

## Depois da instalação

1. Conecte o leitor USB.
2. Insira o cartão A3.
3. Certifique-se de que o middleware do certificado está instalado.
4. Volte ao ÔMEGA.
5. Clique em **Detectar dispositivo**.
6. Se o certificado aparecer, selecione-o.
7. Confira os dados exibidos.
8. Salve o certificado A3.
9. Use **Testar acesso** quando quiser testar a assinatura.
10. Informe o PIN somente na janela solicitada.

## O que o Bridge procura automaticamente

O instalador procura bibliotecas PKCS#11 comuns, incluindo:

```text
C:\Windows\System32\aetpkss1.dll
C:\Windows\SysWOW64\aetpkss1.dll
C:\Windows\System32\eTPKCS11.dll
C:\Windows\SysWOW64\eTPKCS11.dll
```

Esses caminhos são candidatos, não garantia de que sejam os corretos para todo fabricante/versão.

## Se não encontrar o leitor

Verifique:

- leitor conectado;
- driver PC/SC;
- cartão inserido;
- middleware instalado;
- cartão reconhecido pelo middleware do fabricante.

## Se encontrar o leitor, mas não o certificado

Normalmente o problema está no middleware ou na biblioteca PKCS#11.

Use o diagnóstico do Bridge para verificar:

- PC/SC;
- leitores encontrados;
- DLL PKCS#11;
- certificados enumerados.

## Segurança

O PIN:

- não é salvo no banco;
- não é salvo no frontend;
- não é colocado em arquivo de configuração;
- não é armazenado pelo Bridge.

A chave privada do A3 permanece no cartão/token.

## Não faça

Não exporte a chave privada para PFX para tentar "facilitar" a integração A3. Isso transforma o problema em outro modelo de segurança.
