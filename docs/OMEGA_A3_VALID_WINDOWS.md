# OMEGA A3 com cartão VALID no Windows

## Fluxo

O cartão A3 permanece no cartão. O navegador não acessa a chave privada diretamente.

```text
Cartão VALID -> Leitora USB -> PC/SC -> SafeSign/SafeNet -> OMEGA Bridge -> navegador -> ÔMEGA
```

O PIN é solicitado apenas durante a assinatura e não é persistido pelo ÔMEGA.

## Cartão VALID

A VALID informa que cartões inteligentes precisam de uma leitora e do software gerenciador correspondente. Para cartões gerenciados por SafeSign, a biblioteca PKCS#11 no Windows é normalmente `C:\Windows\System32\aetpkss1.dll`; para SafeNet, `C:\Windows\System32\eTPKCS11.dll`.

O Bridge agora tenta localizar automaticamente essas bibliotecas. Se não encontrar, `OMEGA_PKCS11_MODULE` pode apontar para a DLL correta.

## Teste

1. Instale o driver da leitora.
2. Instale o gerenciador indicado para o cartão (SafeSign/SafeNet).
3. Conecte a leitora e insira o cartão.
4. Inicie `bridge/run_windows.bat`.
5. No ÔMEGA, abra Certificados e escolha A3.
6. Clique em **Detectar dispositivo**.
7. O ÔMEGA consulta PC/SC, identifica a DLL PKCS#11 e enumera os certificados do cartão.
8. Selecione o certificado detectado e cadastre-o como PF ou PJ.
9. Para validar a chave privada, use **Testar certificado**; o PIN é solicitado somente no momento da assinatura.

## Diagnóstico

O Bridge expõe `/diagnostics` para informar:

- leitores PC/SC encontrados;
- erro de PC/SC, se houver;
- DLL PKCS#11 localizada;
- plataforma do computador.

Não há exportação da chave privada do cartão.
