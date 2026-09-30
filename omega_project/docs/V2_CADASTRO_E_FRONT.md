# V2 — Cadastro e organização do Front

- Base real incluída em `dados/CADASTRO.xlsx`.
- Cadastro de empresas separado em Cadastro Rápido e Cadastro Manual.
- Cadastro Rápido recebe CNPJ, IE, IM, e-mail, NIRE, regime e data de entrada.
- Atualização cadastral bloqueia o regime tributário na tela comum.
- Inativação solicita data de saída e preserva o registro.
- Tela Empresas organizada com abas Ativas/Inativas, busca e painel lateral.
- Painel da empresa mostra identificação, regime, inscrições, endereço, contato, certidões e sincronização.
- Front usa `VITE_API_URL`.
- Backend inclui rotas de inativação/reativação e detalhes de certidão.
- Importador `backend/scripts/importar_cadastro.py` usa CNPJ como chave e evita duplicidade.
