# RELATÓRIO DE CORREÇÕES — ÔMEGA

Correções aplicadas:
- Dashboard: contagem distinta de empresas regulares; indicadores de certidões excluem empresas inativas; status de automações normalizados; estados de pendências tratados de forma consistente.
- BrasilAPI: respostas JSON inválidas ou de formato inesperado geram erro controlado.

O pacote preserva código, configurações e banco de dados. Pastas geradas, caches, storage, ZIPs aninhados e entradas duplicadas/corrompidas foram excluídos para reduzir o risco de falha de extração.
Antes de usar em produção, execute os testes do backend e o build do frontend. O arquivo backend/.env pode conter segredos; mantenha o ZIP privado.
