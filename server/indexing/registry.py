"""Per-vault VaultIndex registry.

Holds at most one VaultIndex per vault name for the lifetime of the
process. Indexes are built lazily on first access. Calls to
``get_index(name)`` always return an index that has been sync-checked
against disk (subject to ``VaultIndex.ensure_fresh``'s internal
rate-limit).
"""

from __future__ import annotations

from indexing.vault_index import VaultIndex
from vault_manager import get_vault

_indexes: dict[str, VaultIndex] = {}


def get_index(vault: str) -> VaultIndex:
    """Return a ready-to-query index for the named vault.

    Builds the index from scratch on first call; on subsequent calls only
    does an incremental ``ensure_fresh`` sweep (which itself rate-limits).
    """
    idx = _indexes.get(vault)
    vault_path = get_vault(vault)
    if idx is None:
        idx = VaultIndex()
        idx.build(vault_path)
        _indexes[vault] = idx
    else:
        idx.ensure_fresh()
    return idx


def invalidate(vault: str) -> None:
    """Drop the cached index for a vault (forces a full rebuild next time)."""
    _indexes.pop(vault, None)


def notify_change(vault: str, path: str, removed: bool = False) -> None:
    """Tell the registry that a single note changed or was deleted.

    Surgically updates an already-built index instead of forcing a full
    rebuild. Does nothing if no index is cached yet (the next read will
    build one from disk anyway).
    """
    idx = _indexes.get(vault)
    if idx is None:
        return
    if removed:
        idx.remove_note(path)
    else:
        idx.refresh_note(path)


def reset() -> None:
    """Drop all cached indexes — used by tests."""
    _indexes.clear()
