from pathlib import Path

from config import get_vault_path

# Resolved-path memoization per vault name. Keyed on the raw path string from
# config, so a vault re-pointed to a new path (or removed) is detected and
# re-validated instead of returning a stale Path.
_vault_cache: dict[str, tuple[str, Path]] = {}


class VaultError(Exception):
    pass


def get_vault(name: str) -> Path:
    path_str = get_vault_path(name)
    if path_str is None:
        _vault_cache.pop(name, None)
        raise VaultError(f"Vault '{name}' is not configured. Use 'add_vault' to add it.")

    cached = _vault_cache.get(name)
    if cached is not None and cached[0] == path_str:
        return cached[1]

    vault = Path(path_str).resolve()
    if not vault.exists():
        raise VaultError(f"Vault path does not exist: {path_str}")
    if not vault.is_dir():
        raise VaultError(f"Vault path is not a folder: {path_str}")

    _vault_cache[name] = (path_str, vault)
    return vault


def reset_cache() -> None:
    """Drop memoized resolved vault paths, forcing re-validation on next get_vault()."""
    _vault_cache.clear()


def resolve_path(vault: Path, relative_path: str) -> Path:
    resolved = (vault / relative_path).resolve()
    if not str(resolved).startswith(str(vault)):
        raise VaultError(f"Path is outside the vault: {relative_path}")
    return resolved


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
