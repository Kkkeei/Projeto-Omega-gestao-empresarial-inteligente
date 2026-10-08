# OMEGA Bridge — A3

O OMEGA Bridge é um serviço local para usar certificados A3 em cartão ou token sem copiar a chave privada para o servidor.

## Fluxo

1. O cartão/token A3 fica conectado ao computador onde o Bridge está instalado.
2. O middleware/driver do fabricante precisa estar instalado e reconhecer o dispositivo.
3. O Bridge usa PC/SC para detectar leitores e PKCS#11 para acessar o certificado/chave.
4. O navegador chama o Bridge em `127.0.0.1:8765`.
5. O PIN é enviado somente durante a assinatura e não é salvo nem logado pelo Bridge.
6. O servidor ÔMEGA recebe somente metadados e resultados necessários da operação; a chave privada permanece no dispositivo.

## Windows

Use `run_windows.bat` ou `run_windows.ps1`. O script cria um ambiente virtual, instala as dependências e pede:

- `OMEGA_BRIDGE_TOKEN`: deve ser igual ao `VITE_OMEGA_BRIDGE_TOKEN` do frontend;
- `OMEGA_PKCS11_MODULE`: caminho completo da DLL PKCS#11 fornecida pelo middleware do seu cartão/token;
- `OMEGA_BRIDGE_ALLOWED_ORIGINS`: inclua a URL exata pela qual o frontend é aberto, por exemplo `http://192.168.0.131:5173`.

O nome e o caminho da DLL variam conforme o fabricante. Não copie uma DLL de outro fabricante só porque o nome parece semelhante.

## Teste rápido

Com o Bridge iniciado:

- `GET /health` deve retornar `status=ok`;
- no ÔMEGA, abra **Certificados → A3 → Detectar dispositivo**;
- selecione o certificado detectado;
- salve o cadastro;
- abra o certificado e use **Testar acesso**;
- informe o PIN somente quando solicitado.

## Segurança

O Bridge não deve ser exposto publicamente. Ele escuta apenas em `127.0.0.1`. Use um token aleatório longo e restrinja as origens permitidas.
