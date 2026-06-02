"""End-to-end tests for index-backed read tools and write-hook invalidation."""

import time

from indexing import registry
from tools.folders import delete_folder, get_vault_tree, move_folder
from tools.metadata import write_frontmatter
from tools.notes import create_note, delete_note, move_note, update_note
from tools.search import search_by_tag, search_notes


def test_search_sees_newly_created_note(tmp_vault):
    create_note("test", "fresh", content="alpha")
    results = search_notes("test", "alpha")
    assert [r["path"] for r in results] == ["fresh.md"]


def test_search_sees_updated_content(tmp_vault):
    create_note("test", "n", content="old")
    search_notes("test", "x")  # warm index
    update_note("test", "n", content="hello new")
    results = search_notes("test", "hello")
    assert [r["path"] for r in results] == ["n.md"]


def test_search_does_not_see_deleted_note(tmp_vault):
    create_note("test", "n", content="findme")
    assert search_notes("test", "findme")
    delete_note("test", "n")
    assert search_notes("test", "findme") == []


def test_search_after_move(tmp_vault):
    create_note("test", "a", content="needle")
    move_note("test", "a", "b")
    results = search_notes("test", "needle")
    assert [r["path"] for r in results] == ["b.md"]


def test_search_by_tag_after_frontmatter_write(tmp_vault):
    create_note("test", "n", content="body")
    search_by_tag("test", "x")  # warm index (no tag yet)
    write_frontmatter("test", "n", {"tags": ["important"]})
    assert search_by_tag("test", "important") == [{"path": "n.md"}]


def test_recursive_folder_delete_invalidates_index(tmp_vault):
    create_note("test", "sub/a", content="alpha")
    create_note("test", "sub/b", content="alpha")
    assert len(search_notes("test", "alpha")) == 2

    delete_folder("test", "sub", recursive=True)
    assert search_notes("test", "alpha") == []


def test_folder_move_invalidates_index(tmp_vault):
    create_note("test", "src/a", content="needle")
    search_notes("test", "needle")  # warm
    move_folder("test", "src", "dst")
    paths = [r["path"] for r in search_notes("test", "needle")]
    assert paths == ["dst/a.md"]


def test_search_folder_filter(tmp_vault):
    create_note("test", "kept/a", content="match")
    create_note("test", "other/b", content="match")
    results = search_notes("test", "match", folder="kept")
    paths = [r["path"] for r in results]
    assert paths == ["kept/a.md"]


def test_get_vault_tree_cached_between_calls(tmp_vault):
    create_note("test", "a", content="x")
    t1 = get_vault_tree("test")
    t2 = get_vault_tree("test")
    assert t1 is t2  # cached identity within same sync window


def test_get_vault_tree_invalidated_when_index_changes(tmp_vault):
    create_note("test", "a", content="x")
    t1 = get_vault_tree("test")
    # Force the rate-limited ensure_fresh to actually run on next call
    idx = registry.get_index("test")
    idx._last_sync_at = 0.0  # noqa: SLF001
    create_note("test", "b", content="y")
    t2 = get_vault_tree("test")
    names1 = {c["name"] for c in t1["children"]}
    names2 = {c["name"] for c in t2["children"]}
    assert "b.md" in names2 and "b.md" not in names1


def test_registry_returns_same_index_per_vault(tmp_vault):
    a = registry.get_index("test")
    b = registry.get_index("test")
    assert a is b


def test_registry_invalidate_drops_cached_index(tmp_vault):
    a = registry.get_index("test")
    registry.invalidate("test")
    b = registry.get_index("test")
    assert a is not b


def test_ensure_fresh_picks_up_external_create(tmp_vault):
    """Edits made outside the MCP server (e.g. from Obsidian) are eventually
    visible after the ensure_fresh rate-limit window expires."""
    idx = registry.get_index("test")
    assert "ext.md" not in idx
    (tmp_vault / "ext.md").write_text("external edit", encoding="utf-8")
    idx._last_sync_at = 0.0  # noqa: SLF001 — bypass rate-limit for the test
    idx.ensure_fresh()
    assert "ext.md" in idx


def test_ensure_fresh_rate_limit_skips_walk(tmp_vault):
    idx = registry.get_index("test")
    # Last sync was just done by get_index → second call should be skipped.
    assert idx.ensure_fresh() is False


def test_ensure_fresh_drops_externally_deleted_note(tmp_vault):
    create_note("test", "gone", content="x")
    idx = registry.get_index("test")
    assert "gone.md" in idx
    (tmp_vault / "gone.md").unlink()
    idx._last_sync_at = 0.0  # noqa: SLF001
    idx.ensure_fresh()
    assert "gone.md" not in idx


def test_notify_change_noop_when_no_cache(tmp_vault):
    # No prior get_index call → no cached index → notify_change is a no-op.
    registry.notify_change("test", "x.md")
    registry.notify_change("test", "y.md", removed=True)
    # Nothing should be cached.
    assert "test" not in registry._indexes  # noqa: SLF001


def test_search_returns_error_for_unknown_vault(tmp_vault):
    result = search_notes("missing", "x")
    assert result == [{"error": "Vault 'missing' is not configured. Use 'add_vault' to add it."}]


def test_search_by_tag_returns_error_for_unknown_vault(tmp_vault):
    result = search_by_tag("missing", "x")
    assert "error" in result[0]


def test_search_skips_hidden_folders_via_index(tmp_vault):
    (tmp_vault / ".obsidian").mkdir()
    (tmp_vault / ".obsidian" / "hidden.md").write_text("secret")
    (tmp_vault / "visible.md").write_text("secret")
    results = search_notes("test", "secret")
    assert [r["path"] for r in results] == ["visible.md"]


def test_rate_limit_window_is_short_enough_for_real_edits(tmp_vault):
    """ensure_fresh should pick up changes after the configured window."""
    idx = registry.get_index("test")
    (tmp_vault / "delayed.md").write_text("delayed", encoding="utf-8")
    # Force sync by overriding the timer instead of sleeping for real seconds.
    idx._last_sync_at = time.monotonic() - 10  # noqa: SLF001
    idx.ensure_fresh()
    assert "delayed.md" in idx
