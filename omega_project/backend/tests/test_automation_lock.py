from pathlib import Path


def test_lock_blocks_second_consultation(monkeypatch, tmp_path: Path):
    import app.db.database as db
    import app.services.automation_lock as lock

    db_path = tmp_path / "lock.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(lock, "DB_PATH", db_path)
    first = lock._acquire_lock_sync("CONSULTA_CERTIDAO_FEDERAL", 1, "Empresa A")
    assert first is not None

    second = lock._acquire_lock_sync("CONSULTA_CERTIDAO_NARRATIVA", 2, "Empresa B")
    assert second is None

    status = lock._status_sync()
    assert status["ocupada"] is True
    assert status["tipo"] == "CONSULTA_CERTIDAO_FEDERAL"
    assert status["empresa"] == "Empresa A"

    lock._release_lock_sync(first["token"])
    assert lock._status_sync()["ocupada"] is False
