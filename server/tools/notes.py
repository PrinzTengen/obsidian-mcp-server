import frontmatter

from indexing import registry
from vault_manager import VaultError, ensure_parent, get_vault, resolve_path


def _ensure_md(path: str) -> str:
    return path if path.endswith(".md") else path + ".md"


def create_note(
    vault: str, path: str, content: str = "", frontmatter_data: dict | None = None
) -> str:
    try:
        vault_path = get_vault(vault)
        note_path = resolve_path(vault_path, _ensure_md(path))
        if note_path.exists():
            return f"Error: Note already exists: {path}"
        ensure_parent(note_path)
        post = frontmatter.Post(content, **(frontmatter_data or {}))
        note_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        registry.notify_change(vault, _ensure_md(path))
        return f"Note created: {path}"
    except VaultError as e:
        return f"Error: {e}"


def read_note(vault: str, path: str) -> dict:
    try:
        vault_path = get_vault(vault)
        note_path = resolve_path(vault_path, _ensure_md(path))
        if not note_path.exists():
            return {"error": f"Note not found: {path}"}
        post = frontmatter.load(str(note_path))
        return {
            "path": path,
            "content": post.content,
            "frontmatter": dict(post.metadata),
        }
    except VaultError as e:
        return {"error": str(e)}


def update_note(
    vault: str, path: str, content: str | None = None, frontmatter_data: dict | None = None
) -> str:
    try:
        vault_path = get_vault(vault)
        note_path = resolve_path(vault_path, _ensure_md(path))
        if not note_path.exists():
            return f"Error: Note not found: {path}"
        post = frontmatter.load(str(note_path))
        if content is not None:
            post.content = content
        if frontmatter_data is not None:
            post.metadata.update(frontmatter_data)
        note_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        registry.notify_change(vault, _ensure_md(path))
        return f"Note updated: {path}"
    except VaultError as e:
        return f"Error: {e}"


def delete_note(vault: str, path: str) -> str:
    try:
        vault_path = get_vault(vault)
        note_path = resolve_path(vault_path, _ensure_md(path))
        if not note_path.exists():
            return f"Error: Note not found: {path}"
        note_path.unlink()
        registry.notify_change(vault, _ensure_md(path), removed=True)
        return f"Note deleted: {path}"
    except VaultError as e:
        return f"Fehler: {e}"


def move_note(vault: str, from_path: str, to_path: str) -> str:
    try:
        vault_path = get_vault(vault)
        src = resolve_path(vault_path, _ensure_md(from_path))
        dst = resolve_path(vault_path, _ensure_md(to_path))
        if not src.exists():
            return f"Error: Note not found: {from_path}"
        if dst.exists():
            return f"Error: Destination already exists: {to_path}"
        ensure_parent(dst)
        src.rename(dst)
        registry.notify_change(vault, _ensure_md(from_path), removed=True)
        registry.notify_change(vault, _ensure_md(to_path))
        return f"Note moved: {from_path} -> {to_path}"
    except VaultError as e:
        return f"Error: {e}"
