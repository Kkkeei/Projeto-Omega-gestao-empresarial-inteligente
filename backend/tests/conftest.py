import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_DIR / "backend"
for path in (PROJECT_DIR, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Os testes são executáveis mesmo quando o pacote foi distribuído sem omega.db.
# O pacote de produção NÃO contém o banco; a suíte cria apenas o schema mínimo
# necessário e uma empresa de teste localmente.
from app.db.database import criar_tabelas, conectar_banco

criar_tabelas()
_con = conectar_banco()
try:
    _con.execute(
        "INSERT OR IGNORE INTO empresas (id, cnpj, razao_social, ativo) VALUES (1, '50410847000112', 'EMPRESA TESTE LTDA', 1)"
    )
    _con.commit()
finally:
    _con.close()
