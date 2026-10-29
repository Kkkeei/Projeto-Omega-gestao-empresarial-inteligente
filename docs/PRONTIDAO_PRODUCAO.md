# Fechamento técnico e prontidão operacional — Plataforma ÔMEGA

## Estado desta entrega

Este documento registra os controles adicionados na branch `fix/certidoes-producao-hardening`. A suíte e o build são validados pelo GitHub Actions, pois o ambiente de trabalho desta revisão não permite executar um clone local. A aprovação do CI confirma compilação e testes automatizados; não substitui a validação ao vivo dos portais fiscais, certificado, SMTP, banco e armazenamento reais.

## Certidões

### SEFAZ-PE (Playwright)
- Consulta usa o CNPJ cadastrado e recusa associar um PDF que não contenha o CNPJ esperado.
- PDFs são armazenados no diretório de certidões configurado e a consulta é gravada no histórico.
- A rota de PDF permite somente arquivos `.pdf` dentro das raízes de armazenamento de certidões, inclusive quando o storage é externo; a API `/api/v1` exige autenticação.
- O estado de validade é distinto da situação fiscal; uma certidão regular pode estar vencida, próxima do vencimento ou ter validade não identificada.
- A classificação e os seletores do portal devem ser confirmados com consulta de teste em conta/ambiente autorizado, porque o e-Fisco pode alterar a interface.

### Federal RFB/PGFN
- O classificador exige frases explícitas; título genérico da página não deve ser interpretado como regularidade.
- A situação fiscal, número e datas são extraídos do texto do PDF capturado; não só do texto transitório do navegador.
- O PDF precisa ter assinatura/estrutura legível por pypdf e conter o CNPJ consultado.
- A resposta da API não entrega o caminho local absoluto, texto integral do portal nem detalhes internos de exceção; falha de armazenamento não é apresentada como consulta concluída.
- O Chrome é executado com perfil isolado e diretório temporário de download. Em Windows, Linux e macOS, a automação encerra somente o processo de navegador que ela abriu e remove o perfil temporário.
- **Limitação operacional:** a automação federal ainda usa PyAutoGUI, clipboard e navegação por teclado. Precisa de uma sessão gráfica ativa, permissões de desktop, navegador instalado e um teste ao vivo no portal da Receita. Um backend headless/serviço sem desktop não deve prometer essa consulta.

### Certidão Narrativa SEFAZ-PE
- Também depende de automação gráfica, certificado configurado e drivers/sessão operacional corretos.
- Precisa de teste ao vivo com certificado autorizado antes do uso geral.

### Certificados A1/A3
- A senha A1 é armazenada criptografada; revelação/baixamento e download do arquivo são ações administrativas e registradas.
- O PIN do A3 não é armazenado pelo servidor.
- O cadastro A3 sem dispositivo fica explicitamente como `NAO_VINCULADO` e não é considerado apto para uso.
- O formulário permite detectar e vincular dispositivo real pelo OMEGA Bridge. A substituição de A3 já vinculado exige detectar o cartão/token novo; um cadastro vazio não pode desativar o vínculo ativo.

### Processamento em lote
- O lote deve apresentar o resumo real e os resultados que precisem de atenção; não é correto sempre mostrar um selo verde de sucesso.
- Falhas inesperadas são registradas nos logs sem devolver detalhes internos diretamente ao usuário.
- Não execute lote amplo antes de validar uma empresa de teste e o funcionamento do portal.

## Configuração para produção

1. Faça backup do banco `backend/omega.db` e de toda a pasta configurada em `OMEGA_STORAGE_PATH`; não substitua nem limpe esses recursos durante atualização.
2. Crie um `.env` no backend a partir do exemplo, sem copiar chaves de exemplo como valores reais.
3. Defina `OMEGA_ENV=production`.
4. Gere `OMEGA_JWT_SECRET` com `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
5. Gere `OMEGA_CERTIFICADO_MASTER_KEY` com `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Guarde-a fora do repositório e faça backup seguro; perdê-la pode impedir a descriptografia de certificados A1 e senhas criptografadas.
6. Defina `OMEGA_ADMIN_EMAIL` e `OMEGA_ADMIN_PASSWORD` na primeira inicialização ou confirme que já existe um administrador ativo.
7. Defina `CORS_ORIGINS` para as origens HTTPS reais, `OMEGA_PUBLIC_REGISTRATION=false` e `OMEGA_FRONTEND_URL`.
8. Configure SMTP (`OMEGA_SMTP_HOST`, `OMEGA_SMTP_PORT`, `OMEGA_SMTP_USER`, `OMEGA_SMTP_PASSWORD`, `OMEGA_SMTP_FROM`, TLS conforme seu provedor). Sem SMTP a recuperação por e-mail não será entregue.
9. Instale Chromium para Playwright com `playwright install chromium`. Para as automações gráficas federais/narrativas, valide Chrome/Chromium, display/sessão, permissão de controle e certificado na máquina onde o backend executa.
10. Execute primeiro uma consulta estadual e uma federal com empresa autorizada, compare CNPJ, situação, validade e PDF com o portal oficial. Só depois use o lote.

## Testes e aceitação

O workflow `.github/workflows/ci.yml` verifica sintaxe Python, testes do backend e Bridge, auditoria de dependências npm e build/TypeScript do frontend. Na execução validada durante esta revisão, a suíte reportou 132 testes de backend aprovados e 3 testes da Bridge aprovados; a compilação do frontend também passou. A auditoria npm reportou zero vulnerabilidades conhecidas na árvore instalada naquele commit. Uma nova execução é necessária após as alterações finais de limpeza e autorização desta PR. O aceite da parte de certidões exige adicionalmente:
- teste de PDF salvo e baixado via API autenticada;
- consulta real SEFAZ-PE e RFB/PGFN, conferindo a certidão emitida com o portal;
- certidão positiva com efeitos de negativa, irregular, vencida, validade ausente e falha técnica;
- concorrência entre duas consultas (lock 409), lote parcial e retomada após falha;
- restart do backend com banco/storage existentes, verificando que nenhum histórico ou PDF desapareceu;
- recuperação de senha por SMTP em ambiente de teste.

## Sequência dos Pull Requests

Há três PRs/linhas de trabalho pré-existentes com dependências importantes:
- PR #1 (impostos, testes e algumas correções de paths) parte de `main`;
- PR #2 (redesign, navegação e certificados) parte de `main`;
- PR #3 (DCTFWeb) está empilhado sobre a branch do PR #2;
- PR #4 (este hardening) deve ser integrado sobre PR #3, depois de CI verde e revisão.

O PR #1 contém alterações que não estão automaticamente incluídas no PR #2/PR #3. Antes de publicação em `main`, reconcilie as alterações por cherry-pick/merge revisado; não descarte nenhuma das branches nem faça squash cego.

## Limitações ainda existentes

- Não há transmissão oficial da DCTFWeb implementada.
- Os fluxos federais/narrativa são automação visual, não API oficial; a estabilidade depende do portal, desktop e certificado.
- A integração SMTP depende da configuração e do provedor em produção.
- A configuração PostgreSQL não foi validada nesta revisão; o banco principal implementado continua usando SQLite.
- O CI automatizado está passando na última execução observada, mas precisa ser confirmado novamente após os commits finais.
- A consulta real SEFAZ-PE, a consulta real RFB/PGFN e a certidão narrativa ainda não foram testadas neste turno com certificados/empresas reais.
- A funcionalidade A3 Bridge depende do driver PKCS#11 e do dispositivo instalado na máquina de uso; SMTP, domínio/CORS, chaves de produção e reinício preservando o banco/storage dependem da configuração do ambiente de implantação.
