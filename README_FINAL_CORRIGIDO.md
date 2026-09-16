# ÔMEGA — Projeto Final Corrigido

## Correções desta versão
- Sincronização BrasilAPI no startup desativada por padrão (`OMEGA_SYNC_ON_STARTUP=false`) para evitar HTTP 429.
- Sincronização manual em lote sequencial com intervalo configurável.
- Retry e tratamento específico de 429/timeout na BrasilAPI.
- Proteção global contra duas automações gráficas simultâneas.
- Automações PyAutoGUI encerram a sessão do Chrome ao final por padrão (`OMEGA_CLOSE_CHROME_HARD=true`).
- Falhas de leitura/captura não retornam mais `AGUARDANDO_INTERVENCAO`; retornam `ERRO`/`Erro técnico`.
- Histórico e persistência continuam preservados.
- ZIP de atualização NÃO inclui `backend/omega.db` nem backups SQLite, para não substituir banco operacional.
- Frontend preparado para uso no host `192.168.100.3` através de `VITE_API_URL`.

## Testes executados
- `pytest -q`: 12 testes aprovados.
- `python -m compileall -q backend`: aprovado.
- TestClient: `/`, `/health`, `/api/v1/empresas`, `/api/v1/certidoes`, `/api/v1/certidoes/tipos`, `/api/v1/certidoes/automacao/status`, `/api/v1/pendencias` e `/api/v1/automacoes/execucoes`: todos 200.

## Observação sobre homologação real
Os testes automatizados não substituem o teste real dos portais públicos e do Chrome/PyAutoGUI em uma sessão gráfica Windows com certificado digital. O pacote está preparado para essa homologação e fecha o Chrome mesmo em falhas.
## Central de Certidões — versão atualizada
- interface reorganizada com cards de Federal, Estadual e Narrativa;
- seleção de empresas em cards com pesquisa;
- painel da empresa selecionada com emissão por tipo;
- seção de PDFs disponíveis para baixar/visualizar a qualquer momento;
- histórico de consultas preservado;
- automação Federal com tentativa automática de aceitar o banner de cookies e fluxo de emissão/PDF por sequência de foco configurável;
- parâmetros da Receita Federal ficam em `backend/.env.example`.


## Interface
A área dedicada "Automações" foi retirada da navegação e do dashboard nesta versão. As rotinas de automação permanecem no backend para retomada posterior e a emissão de certidões continua sendo acessível pela Central de Certidões.
