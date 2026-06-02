from tools.metadata import (
    get_backlinks,
    get_outlinks,
    read_frontmatter,
    write_frontmatter,
)


def test_read_frontmatter(tmp_vault):
    (tmp_vault / "n.md").write_text("---\ntitle: Hi\ntags: [a]\n---\nbody")
    result = read_frontmatter("test", "n")
    assert result["frontmatter"] == {"title": "Hi", "tags": ["a"]}


def test_read_frontmatter_missing(tmp_vault):
    assert "error" in read_frontmatter("test", "nope")


def test_write_frontmatter_merge(tmp_vault):
    (tmp_vault / "n.md").write_text("---\na: 1\n---\nbody")
    write_frontmatter("test", "n", {"b": 2}, merge=True)
    assert read_frontmatter("test", "n")["frontmatter"] == {"a": 1, "b": 2}


def test_write_frontmatter_replace(tmp_vault):
    (tmp_vault / "n.md").write_text("---\na: 1\n---\nbody")
    write_frontmatter("test", "n", {"b": 2}, merge=False)
    assert read_frontmatter("test", "n")["frontmatter"] == {"b": 2}


def test_write_frontmatter_missing_returns_error(tmp_vault):
    assert write_frontmatter("test", "nope", {"a": 1}).startswith("Error")


def test_get_backlinks_finds_wikilink(tmp_vault):
    (tmp_vault / "target.md").write_text("hi")
    (tmp_vault / "src.md").write_text("see [[target]]")
    result = get_backlinks("test", "target")
    assert [r["path"] for r in result] == ["src.md"]


def test_get_backlinks_finds_with_alias(tmp_vault):
    (tmp_vault / "target.md").write_text("hi")
    (tmp_vault / "src.md").write_text("see [[target|nicer name]]")
    assert [r["path"] for r in get_backlinks("test", "target")] == ["src.md"]


def test_get_backlinks_ignores_other_notes(tmp_vault):
    (tmp_vault / "target.md").write_text("hi")
    (tmp_vault / "other.md").write_text("see [[different]]")
    assert get_backlinks("test", "target") == []


def test_get_outlinks_wikilinks_and_mdlinks(tmp_vault):
    (tmp_vault / "n.md").write_text(
        "intro [[other]] and [link](file.md) and [web](https://example.com)"
    )
    out = get_outlinks("test", "n")
    types = [(o["type"], o["target"]) for o in out]
    assert ("wikilink", "other") in types
    assert ("mdlink", "file.md") in types
    assert all(t[1] != "https://example.com" for t in types)


def test_get_outlinks_wikilink_with_alias(tmp_vault):
    (tmp_vault / "n.md").write_text("[[target|shown]]")
    out = get_outlinks("test", "n")
    assert out[0]["target"] == "target"


def test_get_outlinks_missing_returns_error(tmp_vault):
    out = get_outlinks("test", "nope")
    assert "error" in out[0]
