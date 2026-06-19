import difflib
import re

from indexing import registry
from vault_manager import VaultError

# Minimum relevance for a fuzzy name match to be returned. Tuned so typos
# ("projkt" -> "Projekt") survive while unrelated notes are dropped.
_MIN_FIND_SCORE = 0.5


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
    needle = query if case_sensitive else query.lower()

    results = []
    for path, note in idx.notes.items():
        if folder_prefix and not (path == folder_prefix or path.startswith(folder_prefix + "/")):
            continue
        # Cheap whole-document membership test skips the expensive splitlines +
        # per-line regex for the vast majority of notes that can't match.
        haystack = note.content if case_sensitive else note.content.lower()
        if needle not in haystack:
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


def _is_subsequence(needle: str, haystack: str) -> bool:
    """True if every char of `needle` appears in `haystack` in order."""
    it = iter(haystack)
    return all(ch in it for ch in needle)


def _match_score(query: str, text: str) -> float:
    """Relevance of `query` against a single candidate string in [0, 1].

    Layered so the strongest signal wins: exact > prefix > substring >
    in-order subsequence, with a typo-tolerant similarity ratio as the floor.
    All inputs are expected lowercased.
    """
    if not text:
        return 0.0
    if query == text:
        return 1.0
    if text.startswith(query):
        return 0.95
    if query in text:
        return 0.85
    ratio = difflib.SequenceMatcher(None, query, text).ratio()
    if _is_subsequence(query, text):
        return max(0.6, ratio)
    return ratio


def find_notes(vault: str, query: str, limit: int = 20) -> list:
    """Fuzzy, typo-tolerant search by note name/title (and path).

    Ranks every indexed note by how well its filename, frontmatter `title`,
    and vault path match the query, then returns the best `limit` hits. Runs
    entirely off the in-memory index (no disk reads), so it stays fast on
    large vaults. Use this to jump to a note you half-remember the name of;
    use `search_notes` for full-text body search.
    """
    try:
        idx = registry.get_index(vault)
    except VaultError as e:
        return [{"error": str(e)}]

    q = query.strip().lower()
    if not q:
        return []

    scored = []
    for path, note in idx.notes.items():
        stem = path.rsplit("/", 1)[-1]
        if stem.endswith(".md"):
            stem = stem[:-3]
        title_val = note.frontmatter.get("title")
        title = str(title_val) if title_val not in (None, "") else stem
        score = max(
            _match_score(q, stem.lower()),
            _match_score(q, title.lower()),
            _match_score(q, path.lower()),
        )
        if score >= _MIN_FIND_SCORE:
            scored.append((score, path, title))

    scored.sort(key=lambda r: (-r[0], r[1]))
    return [
        {"path": path, "title": title, "score": round(score, 3)}
        for score, path, title in scored[: max(0, limit)]
    ]
