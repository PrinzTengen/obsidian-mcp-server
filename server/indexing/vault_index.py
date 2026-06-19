"""In-memory index of an Obsidian vault.

Scaffolding for later acceleration of search, backlink, and tag queries.
Does not change tool behaviour — existing tools keep reading the filesystem
directly. The index is opt-in for new callers.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
_MDLINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_INLINE_TAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_/-]+)")


@dataclass
class IndexedNote:
    """Cached metadata for a single note.

    All fields reflect the state of the file at the time it was last indexed.
    """

    path: str
    content: str
    frontmatter: dict
    tags: set[str] = field(default_factory=set)
    outlinks: list[str] = field(default_factory=list)
    mtime: float = 0.0
    size: int = 0


# Backwards-compatible alias mentioned in the original ticket.
CachedNote = IndexedNote


class VaultIndex:
    """In-memory map of relative path -> IndexedNote.

    Typical usage:
        idx = VaultIndex()
        idx.build(vault_path)
        idx.refresh_note("notes/today.md")
        idx.remove_note("notes/old.md")
    """

    def __init__(self) -> None:
        self._notes: dict[str, IndexedNote] = {}
        self._vault_path: Path | None = None
        self._last_sync_at: float = 0.0

    # ── Public read API ───────────────────────────────────────────────────────

    @property
    def vault_path(self) -> Path | None:
        return self._vault_path

    @property
    def last_sync_at(self) -> float:
        """Monotonic timestamp of the most recent build/ensure_fresh sweep."""
        return self._last_sync_at

    @property
    def notes(self) -> dict[str, IndexedNote]:
        """Read-only view of all indexed notes (do not mutate)."""
        return self._notes

    def get(self, path: str) -> IndexedNote | None:
        return self._notes.get(self._normalize(path))

    def __contains__(self, path: str) -> bool:
        return self._normalize(path) in self._notes

    def __len__(self) -> int:
        return len(self._notes)

    # ── Mutation API ──────────────────────────────────────────────────────────

    def build(self, vault_path: Path | str) -> None:
        """Scan the vault from scratch.

        Replaces any prior state. Skips files inside hidden folders (e.g.
        `.obsidian/`, `.trash/`) — those directories are never descended into.
        """
        self._vault_path = Path(vault_path).resolve()
        self._notes.clear()
        for entry in self._iter_markdown_entries(self._vault_path):
            note = self._read_entry(entry)
            if note is not None:
                self._notes[note.path] = note
        self._last_sync_at = time.monotonic()

    def ensure_fresh(self, max_age_seconds: float = 2.0) -> bool:
        """Incrementally sync the index with disk if it has gone stale.

        Walks the vault with a single ``os.scandir`` pass. On most platforms
        (notably Windows) the directory entry already carries ``st_mtime`` and
        ``st_size``, so ``entry.stat()`` issues no extra syscall — we re-read
        only notes whose mtime or size changed, add notes missing from the
        index, and drop notes whose files no longer exist. Hidden directories
        are pruned, never descended into. Skips the sweep entirely if the last
        sync was within ``max_age_seconds`` — this makes multiple tool calls in
        the same conversational turn essentially free.

        Returns True if a sync ran, False if it was skipped.
        """
        if self._vault_path is None:
            raise RuntimeError("VaultIndex.ensure_fresh called before build()")
        if time.monotonic() - self._last_sync_at < max_age_seconds:
            return False

        seen: set[str] = set()
        for entry in self._iter_markdown_entries(self._vault_path):
            try:
                stat = entry.stat()
            except OSError:
                continue
            rel = self._rel(entry.path)
            seen.add(rel)
            cached = self._notes.get(rel)
            if cached is None or cached.mtime != stat.st_mtime or cached.size != stat.st_size:
                note = self._read_entry(entry, stat=stat)
                if note is not None:
                    self._notes[note.path] = note
        for rel in list(self._notes.keys()):
            if rel not in seen:
                del self._notes[rel]

        self._last_sync_at = time.monotonic()
        return True

    def refresh_note(self, path: str) -> IndexedNote | None:
        """Re-read a single note from disk.

        Adds it to the index if missing, updates it if it exists, removes it
        if the file no longer exists. Returns the indexed note (or None if it
        was removed).
        """
        if self._vault_path is None:
            raise RuntimeError("VaultIndex.refresh_note called before build()")
        rel = self._normalize(path)
        file_path = self._vault_path / rel
        if not file_path.exists():
            self._notes.pop(rel, None)
            return None
        note = self._read_note(str(file_path))
        if note is None:
            self._notes.pop(rel, None)
            return None
        self._notes[note.path] = note
        return note

    def set_note(self, path: str, content: str, fm: dict) -> IndexedNote | None:
        """Update a note from already-parsed content, without re-reading body.

        Used right after a write, when the caller already holds the note's
        content and frontmatter — this avoids a redundant ``frontmatter.load``
        of the file we just wrote. Only ``stat()`` is touched, for mtime/size.
        Returns None if the file cannot be stat'd (falls back to nothing).
        """
        if self._vault_path is None:
            raise RuntimeError("VaultIndex.set_note called before build()")
        rel = self._normalize(path)
        file_path = self._vault_path / rel
        try:
            stat = file_path.stat()
        except OSError:
            return None
        fm = dict(fm)
        note = IndexedNote(
            path=rel,
            content=content,
            frontmatter=fm,
            tags=self._collect_tags(fm, content),
            outlinks=self._collect_outlinks(content),
            mtime=stat.st_mtime,
            size=stat.st_size,
        )
        self._notes[rel] = note
        return note

    def remove_note(self, path: str) -> None:
        """Drop a note from the index. No-op if it isn't present."""
        self._notes.pop(self._normalize(path), None)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _normalize(self, path: str) -> str:
        rel = path.replace("\\", "/").lstrip("/")
        if not rel.endswith(".md"):
            rel = rel + ".md"
        return rel

    def _rel(self, full_path: str) -> str:
        """Vault-relative POSIX path for an absolute file under the vault.

        Computed via ``os.path.relpath`` against the already-resolved vault
        root — no per-file ``Path.resolve()`` syscall.
        """
        assert self._vault_path is not None
        return os.path.relpath(full_path, self._vault_path).replace("\\", "/")

    def _iter_markdown_entries(self, vault_path: Path):
        """Yield ``os.DirEntry`` for every ``.md`` file outside hidden folders.

        Uses an explicit ``os.scandir`` stack so hidden directories are pruned
        before descent (we never enter ``.obsidian/``, ``.git/``, ``.trash/``)
        and so the yielded entries carry cached stat data.
        """
        stack: list[str] = [str(vault_path)]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        if entry.name.startswith("."):
                            continue
                        try:
                            is_dir = entry.is_dir(follow_symlinks=False)
                        except OSError:
                            continue
                        if is_dir:
                            stack.append(entry.path)
                        elif entry.name.endswith(".md"):
                            yield entry
            except OSError:
                continue

    def _read_entry(self, entry: os.DirEntry, stat=None) -> IndexedNote | None:
        try:
            if stat is None:
                stat = entry.stat()
        except OSError:
            return None
        return self._read_note(entry.path, stat=stat)

    def _read_note(self, file_path: str, stat=None) -> IndexedNote | None:
        assert self._vault_path is not None
        try:
            if stat is None:
                stat = os.stat(file_path)
            post = frontmatter.load(file_path)
        except (OSError, ValueError):
            return None

        rel = self._rel(file_path)
        content = post.content
        fm = dict(post.metadata)

        return IndexedNote(
            path=rel,
            content=content,
            frontmatter=fm,
            tags=self._collect_tags(fm, content),
            outlinks=self._collect_outlinks(content),
            mtime=stat.st_mtime,
            size=stat.st_size,
        )

    @staticmethod
    def _collect_tags(fm: dict, content: str) -> set[str]:
        tags: set[str] = set()

        fm_tags = fm.get("tags", [])
        if isinstance(fm_tags, str):
            fm_tags = [fm_tags]
        for t in fm_tags or []:
            if not isinstance(t, str):
                continue
            tag = t.lstrip("#").strip()
            if tag:
                tags.add(tag)

        for match in _INLINE_TAG_RE.finditer(content):
            tags.add(match.group(1))

        return tags

    @staticmethod
    def _collect_outlinks(content: str) -> list[str]:
        out: list[str] = []
        for match in _WIKILINK_RE.finditer(content):
            target = match.group(1).strip()
            if target:
                out.append(target)
        for match in _MDLINK_RE.finditer(content):
            url = match.group(2)
            if not url.startswith(("http://", "https://")):
                out.append(url)
        return out
