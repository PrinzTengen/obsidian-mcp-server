import sys
from pathlib import Path

import pytest

SERVER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER_DIR))

import config  # noqa: E402
import vault_manager  # noqa: E402
from indexing import registry as index_registry  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_caches():
    """Wipe per-process caches between tests so they can't leak state."""
    index_registry.reset()
    try:
        from tools import folders as _folders

        _folders._tree_cache.clear()
    except Exception:
        pass
    yield


@pytest.fixture
def tmp_vault(tmp_path, monkeypatch):
    """Create a temporary vault directory and register it as vault 'test'.

    Patches vault_manager.get_vault_path (which was bound at import time via
    `from config import get_vault_path`) so tools resolve 'test' to this tmp
    dir without touching the user's real ~/.obsidian-mcp/config.json.
    """
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    vaults = {"test": str(vault_dir)}
    lookup = lambda name: vaults.get(name)  # noqa: E731
    monkeypatch.setattr(vault_manager, "get_vault_path", lookup)
    monkeypatch.setattr(config, "get_vault_path", lookup)
    return vault_dir


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Redirect CONFIG_DIR / CONFIG_FILE into tmp_path for config.py tests."""
    cfg_dir = tmp_path / ".obsidian-mcp"
    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", cfg_dir / "config.json")
    return cfg_dir
