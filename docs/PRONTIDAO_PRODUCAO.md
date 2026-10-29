# Fechamento técnico e prontidão operacional — Plataforma ÔMEGA

## Estado desta entrega

Este documento registra os controles adicionados na branch `fix/certidoes-producao-hardening`. Ele não equivale a uma certificação de produção: o ambiente de execução desta revisão não teve acesso de rede ao GitHub por `git clone`, e não foi possível executar a suíte nem o build localmente. O CI deve ser usado como validação obrigatória antes de mesclar.

## Certidões

### SEFAZ-PE (Playwright)
- Consulta usa o CNPJ cadastrado e classifica texto extraído do PDF.
- PDFs são armazenados no diretório de certidões configurado e a consulta é gravada no histórico.
- O caminho servido pela API é validado contra a área de armazenamento de certidões, incluindo a configuração de storage externo.
- O estado de validade é distinto da situação fiscal; uma certidão regular pode estar vencida ou próxima do vencimento.
- A classificação e os seletores do portal devem ser confirmados com consulta de teste em conta/ambiente autorizado, porque o e-Fisco pode alterar a interface.

### Federal RFB/PGFN
- O classificador exige frases explícitas; título genérico da página não deve ser interpretado como regularidade.
- Datas são validadas como datas reais.
- O arquivo capturado precisa ter assinatura PDF e uma estrutura legível por pypdf.
- A resposta da API não entrega o caminho local absoluto, texto integral do portal nem detalhes internos de exceção.
- O Chrome é executado com perfil isolado. Em Linux/macOS, o processo é encerrado pelo grupo de processos próprio; o perfil temporário é removido.
- **Limitação operacional:** a automação federal ainda usa PyAutoGUI, clipboard e navegação por teclado. Precisa de uma sessão gráfica ativa, permissões de desktop, navegador instalado e um teste ao vivo no portal da Receita. Um backend headless/serviço sem desktop não deve prometer essa consulta.

### Certidão Narrativa SEFAZ-PE
- Também depende de automação gráfica e certificado configurado. Precisa de teste ao vivo com o certificado autorizado e os drivers/sessão operacional corretos.

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

O workflow `.github/workflows/ci.yml` verifica sintaxe Python, testes do backend e bridge, e build/TypeScript do frontend. O aceite da parte de certidões exige adicionalmente:
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
- Sem build e testes executados no ambiente de CI, a entrega não está formalmente aprovada para produção.
