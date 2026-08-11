import os

import config


def test_get_config_returns_empty_when_no_file(isolated_config):
    assert config.get_config() == {"vaults": {}}


def test_add_and_get_vault(isolated_config):
    config.add_vault("notes", "/tmp/notes")
    assert config.get_vault_path("notes") == "/tmp/notes"
    assert config.list_vaults() == {"notes": "/tmp/notes"}


def test_get_vault_path_unknown_returns_none(isolated_config):
    assert config.get_vault_path("missing") is None


def test_remove_vault(isolated_config):
    config.add_vault("a", "/a")
    config.add_vault("b", "/b")
    config.remove_vault("a")
    assert config.list_vaults() == {"b": "/b"}


def test_remove_unknown_vault_is_noop(isolated_config):
    config.add_vault("a", "/a")
    config.remove_vault("nope")
    assert config.list_vaults() == {"a": "/a"}


def test_save_creates_config_dir(isolated_config):
    config.add_vault("a", "/a")
    assert (isolated_config / "config.json").exists()


def test_unicode_paths_round_trip(isolated_config):
    config.add_vault("Lernen", "/Users/me/Obsidian Vault/Lärnings")
    assert config.get_vault_path("Lernen") == "/Users/me/Obsidian Vault/Lärnings"


def test_get_config_does_not_reread_file_when_unchanged(isolated_config, monkeypatch):
    config.add_vault("a", "/a")
    config.reset_cache()  # simulate a fresh process that hasn't read the file yet

    calls = []
    original = config._read_config_file

    def spy():
        calls.append(1)
        return original()

    monkeypatch.setattr(config, "_read_config_file", spy)

    config.get_config()
    config.get_config()
    config.get_vault_path("a")

    assert len(calls) == 1


def test_get_config_rereads_after_file_changes_on_disk(isolated_config):
    config.add_vault("a", "/a")
    first = config.get_config()
    assert first == {"vaults": {"a": "/a"}}

    # Write directly (bypassing save_config) and force the mtime forward, since
    # some filesystems have coarse mtime resolution and a same-tick write
    # wouldn't otherwise be observable as "changed".
    config.CONFIG_FILE.write_text('{"vaults": {"a": "/a", "b": "/b"}}', encoding="utf-8")
    new_mtime = config.CONFIG_FILE.stat().st_mtime + 5
    os.utime(config.CONFIG_FILE, (new_mtime, new_mtime))

    second = config.get_config()
    assert second == {"vaults": {"a": "/a", "b": "/b"}}


def test_get_config_cache_keyed_on_path_not_leaked_across_isolated_configs(tmp_path, monkeypatch):
    # Two different CONFIG_FILE targets (as isolated_config does per-test) must
    # not share a cache entry, even if both happen to be "file does not exist".
    cfg_dir_a = tmp_path / "a" / ".obsidian-mcp"
    cfg_dir_b = tmp_path / "b" / ".obsidian-mcp"

    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir_a)
    monkeypatch.setattr(config, "CONFIG_FILE", cfg_dir_a / "config.json")
    config.reset_cache()
    config.add_vault("a", "/a")
    assert config.get_config() == {"vaults": {"a": "/a"}}

    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir_b)
    monkeypatch.setattr(config, "CONFIG_FILE", cfg_dir_b / "config.json")
    assert config.get_config() == {"vaults": {}}
