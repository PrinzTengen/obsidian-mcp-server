from tools.search import search_by_tag, search_notes


def test_search_notes_finds_matches(tmp_vault):
    (tmp_vault / "a.md").write_text("hello world\nfoo")
    (tmp_vault / "b.md").write_text("nothing here")
    results = search_notes("test", "hello")
    assert len(results) == 1
    assert results[0]["path"] == "a.md"
    assert results[0]["matches"] == 1
    assert results[0]["snippets"][0]["text"] == "hello world"


def test_search_notes_case_insensitive_by_default(tmp_vault):
    (tmp_vault / "a.md").write_text("Hello")
    assert len(search_notes("test", "hello")) == 1


def test_search_notes_case_sensitive(tmp_vault):
    (tmp_vault / "a.md").write_text("Hello")
    assert search_notes("test", "hello", case_sensitive=True) == []


def test_search_notes_sorted_by_match_count(tmp_vault):
    (tmp_vault / "few.md").write_text("x")
    (tmp_vault / "many.md").write_text("x\nx\nx")
    results = search_notes("test", "x")
    assert results[0]["path"] == "many.md"
    assert results[1]["path"] == "few.md"


def test_search_notes_skips_hidden_folders(tmp_vault):
    (tmp_vault / ".obsidian").mkdir()
    (tmp_vault / ".obsidian" / "hidden.md").write_text("secret")
    (tmp_vault / "visible.md").write_text("secret")
    results = search_notes("test", "secret")
    paths = [r["path"] for r in results]
    assert paths == ["visible.md"]


def test_search_by_tag_frontmatter(tmp_vault):
    (tmp_vault / "a.md").write_text("---\ntags: [learning, python]\n---\nbody")
    (tmp_vault / "b.md").write_text("---\ntags: [other]\n---\nbody")
    results = search_by_tag("test", "learning")
    assert [r["path"] for r in results] == ["a.md"]


def test_search_by_tag_inline(tmp_vault):
    (tmp_vault / "a.md").write_text("some text #idea inline")
    (tmp_vault / "b.md").write_text("no tag")
    results = search_by_tag("test", "idea")
    assert [r["path"] for r in results] == ["a.md"]


def test_search_by_tag_strips_hash(tmp_vault):
    (tmp_vault / "a.md").write_text("---\ntags: [todo]\n---\nbody")
    assert search_by_tag("test", "#todo") == [{"path": "a.md"}]


def test_search_by_tag_does_not_match_word_extensions(tmp_vault):
    # \w-boundary: '#learningx' should NOT match 'learning'
    (tmp_vault / "a.md").write_text("text #learningx more")
    assert search_by_tag("test", "learning") == []


def test_search_by_tag_frontmatter_as_string(tmp_vault):
    (tmp_vault / "a.md").write_text("---\ntags: solo\n---\nbody")
    assert search_by_tag("test", "solo") == [{"path": "a.md"}]
