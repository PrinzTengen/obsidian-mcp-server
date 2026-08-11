import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".obsidian-mcp"
CONFIG_FILE = CONFIG_DIR / "config.json"

# In-memory cache of the parsed config, keyed by (path, mtime) so a change to
# CONFIG_FILE on disk - or a monkeypatch of CONFIG_FILE in tests - reliably
# invalidates it. `mtime is None` means "file did not exist at last check".
_cache: dict | None = None
_cache_key: tuple[Path, float | None] | None = None


def _read_config_file() -> dict:
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_config() -> dict:
    global _cache, _cache_key

    try:
        mtime = CONFIG_FILE.stat().st_mtime
    except FileNotFoundError:
        mtime = None

    key = (CONFIG_FILE, mtime)
    if _cache is not None and _cache_key == key:
        return _cache

    config = _read_config_file() if mtime is not None else {"vaults": {}}
    _cache = config
    _cache_key = key
    return config


def save_config(config: dict) -> None:
    global _cache, _cache_key
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    _cache = config
    _cache_key = (CONFIG_FILE, CONFIG_FILE.stat().st_mtime)


def reset_cache() -> None:
    """Drop the in-memory config cache, forcing the next get_config() to hit disk."""
    global _cache, _cache_key
    _cache = None
    _cache_key = None


def get_vault_path(name: str) -> str | None:
    return get_config().get("vaults", {}).get(name)


def list_vaults() -> dict:
    return get_config().get("vaults", {})


def add_vault(name: str, path: str) -> None:
    config = get_config()
    config.setdefault("vaults", {})[name] = path
    save_config(config)


def remove_vault(name: str) -> None:
    config = get_config()
    config.setdefault("vaults", {}).pop(name, None)
    save_config(config)
