# Certificados Digitais — PF e A3 com leitor/cartão

## Pessoa Física

A Pessoa Física agora é uma entidade própria no módulo de certificados. O sistema não cria empresa fictícia para representar CPF.

- `pessoas_fisicas`: cadastro do CPF e dados básicos;
- `certificados_pf`: certificados A1/A3 vinculados à pessoa;
- histórico e uso próprios para PF;
- A1 PF: PFX/P12 criptografado e senha criptografada separadamente;
- A3 PF: somente metadados; chave privada e PIN permanecem no cartão/token.

## A3 com leitor

O A3 é usado pelo OMEGA Bridge no computador em que o leitor/cartão está conectado.

1. Instalar driver/middleware do fabricante.
2. Instalar o OMEGA Bridge.
3. Configurar `OMEGA_PKCS11_MODULE` com a DLL/arquivo PKCS#11 do middleware.
4. Configurar o mesmo token em `VITE_OMEGA_BRIDGE_TOKEN`.
5. Incluir a origem do frontend em `OMEGA_BRIDGE_ALLOWED_ORIGINS`.
6. Abrir Certificados → A3 → Detectar dispositivo.
7. Selecionar o certificado encontrado e salvar.
8. Para testar assinatura, o ÔMEGA solicita o PIN localmente; o PIN não é persistido.

O Bridge escuta somente em `127.0.0.1` por padrão.

## Windows

Use `bridge/run_windows.bat`. O script cria o ambiente virtual, instala PySCard/python-pkcs11 e inicia o Bridge. O caminho da DLL PKCS#11 deve ser informado conforme o middleware efetivamente instalado.

O sistema não deve receber nem armazenar a chave privada exportada de um A3.
