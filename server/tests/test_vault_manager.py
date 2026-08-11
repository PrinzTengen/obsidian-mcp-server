from pathlib import Path

import pytest

import vault_manager
from vault_manager import VaultError, get_vault, resolve_path


def test_get_vault_unknown_raises(monkeypatch):
    monkeypatch.setattr(vault_manager, "get_vault_path", lambda name: None)
    with pytest.raises(VaultError, match="not configured"):
        get_vault("missing")


def test_get_vault_missing_path_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(vault_manager, "get_vault_path", lambda name: str(tmp_path / "nope"))
    with pytest.raises(VaultError, match="does not exist"):
        get_vault("x")


def test_get_vault_not_a_directory(tmp_path, monkeypatch):
    file_path = tmp_path / "afile.txt"
    file_path.write_text("hi")
    monkeypatch.setattr(vault_manager, "get_vault_path", lambda name: str(file_path))
    with pytest.raises(VaultError, match="not a folder"):
        get_vault("x")


def test_get_vault_returns_resolved_path(tmp_vault):
    result = get_vault("test")
    assert result == tmp_vault.resolve()


def test_resolve_path_joins_inside_vault(tmp_vault):
    target = resolve_path(tmp_vault, "sub/note.md")
    assert str(target).startswith(str(tmp_vault))
    assert target.name == "note.md"


def test_resolve_path_blocks_traversal(tmp_vault):
    with pytest.raises(VaultError, match="outside the vault"):
        resolve_path(tmp_vault, "../escape.md")


def test_resolve_path_blocks_absolute_outside(tmp_vault, tmp_path):
    outside = tmp_path / "outside.md"
    with pytest.raises(VaultError, match="outside the vault"):
        resolve_path(tmp_vault, str(outside))


def _count_calls(monkeypatch, cls, method_name):
    calls = []
    original = getattr(cls, method_name)

    def counting(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(cls, method_name, counting)
    return calls


def test_get_vault_memoizes_resolved_path(tmp_vault, monkeypatch):
    expected = tmp_vault.resolve()  # resolve once, before counting starts

    resolve_calls = _count_calls(monkeypatch, Path, "resolve")
    exists_calls = _count_calls(monkeypatch, Path, "exists")
    is_dir_calls = _count_calls(monkeypatch, Path, "is_dir")

    for _ in range(3):
        result = get_vault("test")
        assert result == expected

    assert len(resolve_calls) == 1
    assert len(exists_calls) == 1
    assert len(is_dir_calls) == 1


def test_get_vault_revalidates_when_path_changes(tmp_vault, tmp_path, monkeypatch):
    other_vault = tmp_path / "other"
    other_vault.mkdir()

    paths = {"test": str(tmp_vault)}
    monkeypatch.setattr(vault_manager, "get_vault_path", lambda name: paths.get(name))

    first = get_vault("test")
    assert first == tmp_vault.resolve()

    paths["test"] = str(other_vault)
    second = get_vault("test")
    assert second == other_vault.resolve()


def test_get_vault_does_not_return_stale_path_after_removal(tmp_vault, monkeypatch):
    paths = {"test": str(tmp_vault)}
    monkeypatch.setattr(vault_manager, "get_vault_path", lambda name: paths.get(name))

    get_vault("test")
    del paths["test"]

    with pytest.raises(VaultError, match="not configured"):
        get_vault("test")
