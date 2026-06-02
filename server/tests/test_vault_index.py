import pytest

from indexing import CachedNote, IndexedNote, VaultIndex


def _write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_build_indexes_all_markdown_notes(tmp_vault):
    _write(tmp_vault / "a.md", "alpha")
    _write(tmp_vault / "sub" / "b.md", "beta")
    _write(tmp_vault / "c.txt", "not markdown")

    idx = VaultIndex()
    idx.build(tmp_vault)

    assert set(idx.notes) == {"a.md", "sub/b.md"}
    assert len(idx) == 2


def test_build_skips_hidden_folders(tmp_vault):
    _write(tmp_vault / ".obsidian" / "workspace.md", "should be skipped")
    _write(tmp_vault / "visible.md", "yes")

    idx = VaultIndex()
    idx.build(tmp_vault)

    assert set(idx.notes) == {"visible.md"}


def test_indexed_note_fields(tmp_vault):
    body = "---\ntitle: Hi\n---\nbody text"
    target = tmp_vault / "n.md"
    _write(target, body)
    stat = target.stat()

    idx = VaultIndex()
    idx.build(tmp_vault)
    note = idx.get("n.md")

    assert isinstance(note, IndexedNote)
    assert note.path == "n.md"
    assert note.content == "body text"
    assert note.frontmatter == {"title": "Hi"}
    assert note.mtime == stat.st_mtime
    assert note.size == stat.st_size


def test_cached_note_is_indexed_note_alias():
    assert CachedNote is IndexedNote


def test_build_collects_frontmatter_tags(tmp_vault):
    _write(tmp_vault / "a.md", "---\ntags: [learning, python]\n---\nbody")
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert idx.get("a.md").tags == {"learning", "python"}


def test_build_collects_frontmatter_tag_as_string(tmp_vault):
    _write(tmp_vault / "a.md", "---\ntags: solo\n---\nbody")
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert idx.get("a.md").tags == {"solo"}


def test_build_collects_inline_tags(tmp_vault):
    _write(tmp_vault / "a.md", "body with #idea and #project/x mid sentence")
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert idx.get("a.md").tags == {"idea", "project/x"}


def test_build_merges_inline_and_frontmatter_tags(tmp_vault):
    _write(tmp_vault / "a.md", "---\ntags: [a]\n---\nbody #b")
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert idx.get("a.md").tags == {"a", "b"}


def test_build_collects_wikilink_outlinks(tmp_vault):
    _write(tmp_vault / "a.md", "see [[other]] and [[deep/nested|alias]]")
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert idx.get("a.md").outlinks == ["other", "deep/nested"]


def test_build_collects_md_link_outlinks_but_skips_http(tmp_vault):
    _write(tmp_vault / "a.md", "[local](file.md) [web](https://example.com)")
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert idx.get("a.md").outlinks == ["file.md"]


def test_get_unknown_returns_none(tmp_vault):
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert idx.get("nope.md") is None


def test_contains(tmp_vault):
    _write(tmp_vault / "a.md", "x")
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert "a.md" in idx
    assert "a" in idx  # path without .md is normalized
    assert "missing.md" not in idx


def test_refresh_note_picks_up_changes(tmp_vault):
    note = tmp_vault / "a.md"
    _write(note, "old")
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert idx.get("a.md").content == "old"

    _write(note, "new content")
    idx.refresh_note("a.md")
    assert idx.get("a.md").content == "new content"


def test_refresh_note_adds_new_note(tmp_vault):
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert "fresh.md" not in idx

    _write(tmp_vault / "fresh.md", "hi")
    idx.refresh_note("fresh.md")
    assert idx.get("fresh.md").content == "hi"


def test_refresh_note_removes_deleted_file(tmp_vault):
    _write(tmp_vault / "a.md", "x")
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert "a.md" in idx

    (tmp_vault / "a.md").unlink()
    result = idx.refresh_note("a.md")
    assert result is None
    assert "a.md" not in idx


def test_refresh_note_before_build_raises(tmp_vault):
    idx = VaultIndex()
    with pytest.raises(RuntimeError):
        idx.refresh_note("a.md")


def test_remove_note_drops_entry(tmp_vault):
    _write(tmp_vault / "a.md", "x")
    idx = VaultIndex()
    idx.build(tmp_vault)
    idx.remove_note("a.md")
    assert "a.md" not in idx


def test_remove_note_unknown_is_noop(tmp_vault):
    idx = VaultIndex()
    idx.build(tmp_vault)
    idx.remove_note("nope.md")  # must not raise


def test_remove_note_does_not_touch_disk(tmp_vault):
    note = tmp_vault / "a.md"
    _write(note, "x")
    idx = VaultIndex()
    idx.build(tmp_vault)
    idx.remove_note("a.md")
    assert note.exists()


def test_build_replaces_prior_state(tmp_vault):
    _write(tmp_vault / "a.md", "x")
    idx = VaultIndex()
    idx.build(tmp_vault)

    (tmp_vault / "a.md").unlink()
    _write(tmp_vault / "b.md", "y")
    idx.build(tmp_vault)
    assert set(idx.notes) == {"b.md"}


def test_path_normalization_accepts_backslashes(tmp_vault):
    _write(tmp_vault / "sub" / "n.md", "x")
    idx = VaultIndex()
    idx.build(tmp_vault)
    assert idx.get("sub\\n.md") is not None
