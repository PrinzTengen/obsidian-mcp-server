"""In-memory index of an Obsidian vault.

Scaffolding for later acceleration of search, backlink, and tag queries.
Does not change tool behaviour — existing tools keep reading the filesystem
directly. The index is opt-in for new callers.
"""

from __future__ import annotations

import re
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

    # ── Public read API ───────────────────────────────────────────────────────

    @property
    def vault_path(self) -> Path | None:
        return self._vault_path

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
        `.obsidian/`, `.trash/`).
        """
        self._vault_path = Path(vault_path).resolve()
        self._notes.clear()
        for md in self._iter_markdown_files(self._vault_path):
            note = self._read_note(md)
            if note is not None:
                self._notes[note.path] = note

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
        note = self._read_note(file_path)
        if note is None:
            self._notes.pop(rel, None)
            return None
        self._notes[note.path] = note
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

    def _iter_markdown_files(self, vault_path: Path):
        for md in vault_path.rglob("*.md"):
            if any(part.startswith(".") for part in md.relative_to(vault_path).parts):
                continue
            yield md

    def _read_note(self, file_path: Path) -> IndexedNote | None:
        assert self._vault_path is not None
        try:
            stat = file_path.stat()
            post = frontmatter.load(str(file_path))
        except (OSError, ValueError):
            return None

        rel = str(file_path.resolve().relative_to(self._vault_path)).replace("\\", "/")
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
