from pathlib import Path

from app.db.database import _resolve_configured_path


def test_relative_path_uses_configured_base_not_working_directory(tmp_path):
    base = tmp_path / "backend"
    base.mkdir()
    result = _resolve_configured_path("./omega.db", base_dir=base)
    assert result == (base / "omega.db").resolve()


def test_absolute_path_is_preserved(tmp_path):
    wanted = (tmp_path / "external" / "omega.db").resolve()
    assert _resolve_configured_path(str(wanted), base_dir=tmp_path) == wanted
