import re
from pathlib import Path

import frontmatter

from indexing import registry
from vault_manager import VaultError, get_vault, resolve_path

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
MDLINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def _ensure_md(path: str) -> str:
    return path if path.endswith(".md") else path + ".md"


def read_frontmatter(vault: str, path: str) -> dict:
    try:
        vault_path = get_vault(vault)
        note_path = resolve_path(vault_path, _ensure_md(path))
        if not note_path.exists():
            return {"error": f"Note not found: {path}"}
        post = frontmatter.load(str(note_path))
        return {"path": path, "frontmatter": dict(post.metadata)}
    except VaultError as e:
        return {"error": str(e)}


def write_frontmatter(vault: str, path: str, fm_data: dict, merge: bool = True) -> str:
    try:
        vault_path = get_vault(vault)
        note_path = resolve_path(vault_path, _ensure_md(path))
        if not note_path.exists():
            return f"Error: Note not found: {path}"
        post = frontmatter.load(str(note_path))
        if merge:
            post.metadata.update(fm_data)
        else:
            post.metadata = fm_data
        note_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        registry.notify_change(
            vault, _ensure_md(path), content=post.content, frontmatter=dict(post.metadata)
        )
        return f"Frontmatter updated: {path}"
    except VaultError as e:
        return f"Error: {e}"


def get_backlinks(vault: str, path: str) -> list:
    try:
        idx = registry.get_index(vault)
    except VaultError as e:
        return [{"error": str(e)}]

    target_stem = Path(_ensure_md(path)).stem.lower()
    target_path = path.lower()
    results = []
    for note_path, note in idx.notes.items():
        for link in note.outlinks:
            link_lower = link.lower()
            if Path(link).stem.lower() == target_stem or link_lower == target_path:
                results.append({"path": note_path, "link_text": f"[[{link}]]"})
                break
    return results


def get_outlinks(vault: str, path: str) -> list:
    try:
        vault_path = get_vault(vault)
        note_path = resolve_path(vault_path, _ensure_md(path))
        if not note_path.exists():
            return [{"error": f"Note not found: {path}"}]
        text = note_path.read_text(encoding="utf-8", errors="ignore")
        results = []
        for match in WIKILINK_RE.finditer(text):
            inner = match.group(1).strip()
            parts = inner.split("|")
            target = parts[0].strip()
            alias = parts[1].strip() if len(parts) > 1 else None
            entry = {"type": "wikilink", "target": target}
            if alias:
                entry["alias"] = alias
            results.append(entry)
        for match in MDLINK_RE.finditer(text):
            url = match.group(2)
            if not url.startswith("http://") and not url.startswith("https://"):
                results.append({"type": "mdlink", "target": url, "alias": match.group(1)})
        return results
    except VaultError as e:
        return [{"error": str(e)}]
