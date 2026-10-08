import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_DIR / "backend"
for path in (PROJECT_DIR, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Nunca permita que a suíte de testes importe/conecte ao banco operacional.
# As variáveis são definidas ANTES dos módulos de aplicação serem importados.
os.environ["OMEGA_DB_PATH"] = str((PROJECT_DIR / ".test_runtime" / "omega_test.sqlite3").resolve())
os.environ["OMEGA_STORAGE_PATH"] = str((PROJECT_DIR / ".test_runtime" / "storage").resolve())
os.environ["OMEGA_JWT_SECRET"] = "test-secret-do-omega-com-mais-de-32-caracteres"
os.environ["OMEGA_RESET_EXPOSE_URL"] = "true"
os.environ["OMEGA_ADMIN_EMAIL"] = "admin@omega.local"
os.environ["OMEGA_ADMIN_PASSWORD"] = "Admin@123"
os.environ["OMEGA_CERTIFICADO_MASTER_KEY"] = "5DFUGXUoWFJHR806QUMzhfF6-RUhUSd6oPQjC4ySkj8="

from app.db.database import criar_tabelas, conectar_banco

TEST_ROOT = PROJECT_DIR / ".test_runtime"
TEST_ROOT.mkdir(parents=True, exist_ok=True)
for old in (TEST_ROOT / "omega_test.sqlite3", TEST_ROOT / "omega_test.sqlite3-wal", TEST_ROOT / "omega_test.sqlite3-shm"):
    old.unlink(missing_ok=True)

criar_tabelas()
_con = conectar_banco()
try:
    _con.execute(
        "INSERT OR IGNORE INTO empresas (id, cnpj, razao_social, ativo) VALUES (1, '50410847000112', 'EMPRESA TESTE LTDA', 1)"
    )
    _con.commit()
finally:
    _con.close()
