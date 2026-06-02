import re

from indexing import registry
from vault_manager import VaultError


def search_notes(
    vault: str,
    query: str,
    folder: str = "",
    case_sensitive: bool = False,
) -> list:
    try:
        idx = registry.get_index(vault)
    except VaultError as e:
        return [{"error": str(e)}]

    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(query), flags)
    folder_prefix = folder.strip("/").replace("\\", "/")

    results = []
    for path, note in idx.notes.items():
        if folder_prefix and not (path == folder_prefix or path.startswith(folder_prefix + "/")):
            continue
        snippets = []
        for i, line in enumerate(note.content.splitlines(), 1):
            if pattern.search(line):
                snippets.append({"line": i, "text": line.strip()})
        if snippets:
            results.append({"path": path, "matches": len(snippets), "snippets": snippets})
    results.sort(key=lambda r: r["matches"], reverse=True)
    return results


def search_by_tag(vault: str, tag: str) -> list:
    try:
        idx = registry.get_index(vault)
    except VaultError as e:
        return [{"error": str(e)}]

    tag_clean = tag.lstrip("#")
    return [{"path": path} for path, note in idx.notes.items() if tag_clean in note.tags]
