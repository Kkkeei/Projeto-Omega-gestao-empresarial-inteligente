# Módulo Faturamento

Camadas:

- `schema.py`: valida os dados recebidos pela API.
- `repository.py`: consultas e gravações SQLite.
- `service.py`: regras de negócio.
- `declaracao_service.py`: cálculo do período + geração do PDF + gravação do histórico.
- `routes.py`: endpoints FastAPI.
- `setup_db.py`: cria as tabelas/índices necessários.
