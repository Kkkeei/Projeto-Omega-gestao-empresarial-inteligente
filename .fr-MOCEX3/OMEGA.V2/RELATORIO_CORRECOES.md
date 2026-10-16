# Correções aplicadas — Projeto ÔMEGA

## Corrigido nesta versão
1. Dashboard: conta empresas distintas com certidão regular; exclui empresas inativas dos indicadores de certidões vencidas/próximas; reconhece o status EM_EXECUCAO nas automações; normaliza status de pendências.
2. BrasilAPI: resposta JSON malformada ou em formato inesperado gera erro controlado BrasilAPIError com status 502.
3. Preservação: os demais arquivos do ZIP original foram mantidos; a pasta storage permanece excluída.

## Pontos que ainda exigem homologação
- A autorização por empresa nas rotas de Documentação e demais módulos depende da política de perfis/segregação da plataforma. Não foi inventada uma política de acesso sem requisito confirmado.
- Certificado A3 em estado NAO_VINCULADO precisa permanecer indisponível para operações que exijam certificado vinculado.
- Faturamento e Impostos exigem testes de negócio para cálculos, duplicidade e competência.
- Integrações de certidões devem ser testadas com provedores e certificados reais.
- O limite de tentativas de login é armazenado em memória e não é compartilhado entre múltiplos workers.
- O cadastro público em /auth/registrar deve ser desabilitado ou protegido em produção se a política não permitir autoinscrição.

## Validação recomendada após extrair
1. Ativar o ambiente virtual do backend.
2. Executar `python -m compileall app`.
3. Executar `pytest -q`.
4. Executar `npm run build` no frontend.
5. Testar login/perfis, empresas, documentos, certidões, automações, faturamento e impostos antes de substituir a instalação em uso.

O pacote pode conter credenciais em arquivos de configuração. Não o publique sem removê-las.
