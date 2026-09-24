# Faturamento — modificações 18/09/2026

- Toda a linha/cartão da empresa na lista principal é clicável e abre o faturamento da empresa.
- A ação Visualizar usa a mesma navegação da linha, com proteção contra carregamento infinito no cliente.
- A tela detalhada foi corrigida para carregar somente os faturamentos do ano visualizado, reduzindo consultas desnecessárias.
- O formulário Informar faturamento usa calendário nativo para escolher a data exata do lançamento.
- O formulário permite selecionar a periodicidade: Mensal, Trimestral, Semestral, Anual ou Personalizado.
- No mensal, a competência é derivada da data escolhida.
- Nas demais periodicidades, os valores continuam sendo gravados por competência mensal para preservar o histórico.
- O lançamento mensal usa atualização quando já existe a combinação empresa + competência, evitando erro de duplicidade ao escolher no calendário uma competência já informada.
- A lista mantém os status: Pendente em <mês> quando há somente um mês pendente e Pendente vários meses quando há mais de um.
- Foram adicionados índices no SQLite para consultas de faturamento por empresa/competência.

Banco de dados: o pacote NÃO contém backend/omega.db, backend/omega.db-shm ou backend/omega.db-wal. O banco real do ambiente deve ser preservado.
