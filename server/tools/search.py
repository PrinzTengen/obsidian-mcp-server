import re
from pathlib import Path

import frontmatter

from vault_manager import VaultError, get_vault

ATTACHMENT_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".mp3",
    ".mp4",
    ".wav",
    ".svg",
    ".excalidraw",
}


def _iter_notes(vault_path: Path, folder: str = "") -> list[Path]:
    base = (vault_path / folder).resolve() if folder else vault_path.resolve()
    return [p for p in base.rglob("*.md") if not any(part.startswith(".") for part in p.parts)]


def search_notes(vault: str, query: str, folder: str = "", case_sensitive: bool = False) -> list:
    try:
        vault_path = get_vault(vault)
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)
        results = []
        for note in _iter_notes(vault_path, folder):
            text = note.read_text(encoding="utf-8", errors="ignore")
            lines = text.splitlines()
            snippets = []
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    snippets.append({"line": i, "text": line.strip()})
            if snippets:
                rel = str(note.relative_to(vault_path)).replace("\\", "/")
                results.append({"path": rel, "matches": len(snippets), "snippets": snippets})
        results.sort(key=lambda r: r["matches"], reverse=True)
        return results
    except VaultError as e:
        return [{"error": str(e)}]


def search_by_tag(vault: str, tag: str) -> list:
    try:
        vault_path = get_vault(vault)
        tag_clean = tag.lstrip("#")
        inline_pattern = re.compile(r"(?<!\w)#" + re.escape(tag_clean) + r"(?!\w)")
        results = []
        for note in _iter_notes(vault_path):
            text = note.read_text(encoding="utf-8", errors="ignore")
            found = False
            try:
                post = frontmatter.loads(text)
                fm_tags = post.metadata.get("tags", [])
                if isinstance(fm_tags, str):
                    fm_tags = [fm_tags]
                if tag_clean in [t.lstrip("#") for t in fm_tags]:
                    found = True
            except Exception:
                pass
            if not found and inline_pattern.search(text):
                found = True
            if found:
                rel = str(note.relative_to(vault_path)).replace("\\", "/")
                results.append({"path": rel})
        return results
    except VaultError as e:
        return [{"error": str(e)}]
