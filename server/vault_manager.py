from pathlib import Path

from config import get_vault_path


class VaultError(Exception):
    pass


def get_vault(name: str) -> Path:
    path_str = get_vault_path(name)
    if path_str is None:
        raise VaultError(f"Vault '{name}' is not configured. Use 'add_vault' to add it.")
    vault = Path(path_str).resolve()
    if not vault.exists():
        raise VaultError(f"Vault path does not exist: {path_str}")
    if not vault.is_dir():
        raise VaultError(f"Vault path is not a folder: {path_str}")
    return vault


def resolve_path(vault: Path, relative_path: str) -> Path:
    resolved = (vault / relative_path).resolve()
    if not str(resolved).startswith(str(vault)):
        raise VaultError(f"Path is outside the vault: {relative_path}")
    return resolved


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
