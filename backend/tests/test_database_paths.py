from pathlib import Path

from app.db.database import _resolve_configured_path


def test_relative_database_path_is_resolved_against_backend_not_cwd(tmp_path):
    backend = tmp_path / "OMEGA.V2" / "backend"
    unrelated_cwd = tmp_path / "other-working-directory"
    backend.mkdir(parents=True)
    unrelated_cwd.mkdir()

    resolved = _resolve_configured_path("./omega.db", base_dir=backend)

    assert resolved == (backend / "omega.db").resolve()
    assert resolved != (unrelated_cwd / "omega.db").resolve()


def test_relative_storage_path_is_resolved_against_backend(tmp_path):
    backend = tmp_path / "OMEGA.V2" / "backend"
    backend.mkdir(parents=True)

    resolved = _resolve_configured_path("../storage", base_dir=backend)

    assert resolved == (backend.parent / "storage").resolve()


def test_absolute_configured_path_is_preserved(tmp_path):
    configured = tmp_path / "persistent-data" / "omega.db"

    resolved = _resolve_configured_path(str(configured), base_dir=tmp_path / "backend")

    assert resolved == configured.resolve()
