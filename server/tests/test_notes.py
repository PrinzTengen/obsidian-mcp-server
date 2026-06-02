from tools.notes import create_note, delete_note, move_note, read_note, update_note


def test_create_note_writes_file(tmp_vault):
    msg = create_note("test", "hello", content="Body")
    assert "created" in msg
    assert (tmp_vault / "hello.md").exists()


def test_create_note_appends_md_extension(tmp_vault):
    create_note("test", "no-ext", content="x")
    assert (tmp_vault / "no-ext.md").exists()


def test_create_note_with_frontmatter(tmp_vault):
    create_note("test", "fm", content="Body", frontmatter_data={"tags": ["a", "b"]})
    data = read_note("test", "fm")
    assert data["frontmatter"] == {"tags": ["a", "b"]}
    assert data["content"] == "Body"


def test_create_note_in_subfolder_creates_parents(tmp_vault):
    create_note("test", "deep/nested/note", content="x")
    assert (tmp_vault / "deep" / "nested" / "note.md").exists()


def test_create_note_duplicate_returns_error(tmp_vault):
    create_note("test", "dup", content="a")
    msg = create_note("test", "dup", content="b")
    assert msg.startswith("Error")


def test_read_note_missing_returns_error(tmp_vault):
    result = read_note("test", "nope")
    assert "error" in result


def test_update_note_replaces_content(tmp_vault):
    create_note("test", "n", content="old")
    update_note("test", "n", content="new")
    assert read_note("test", "n")["content"] == "new"


def test_update_note_merges_frontmatter(tmp_vault):
    create_note("test", "n", content="x", frontmatter_data={"a": 1})
    update_note("test", "n", frontmatter_data={"b": 2})
    fm = read_note("test", "n")["frontmatter"]
    assert fm == {"a": 1, "b": 2}


def test_update_note_missing_returns_error(tmp_vault):
    assert update_note("test", "nope", content="x").startswith("Error")


def test_delete_note(tmp_vault):
    create_note("test", "n")
    delete_note("test", "n")
    assert not (tmp_vault / "n.md").exists()


def test_delete_note_missing_returns_error(tmp_vault):
    assert delete_note("test", "nope").startswith(("Error", "Fehler"))


def test_move_note(tmp_vault):
    create_note("test", "src", content="x")
    move_note("test", "src", "dst")
    assert not (tmp_vault / "src.md").exists()
    assert (tmp_vault / "dst.md").exists()


def test_move_note_to_existing_returns_error(tmp_vault):
    create_note("test", "a")
    create_note("test", "b")
    assert move_note("test", "a", "b").startswith("Error")


def test_unknown_vault_returns_error(tmp_vault):
    msg = create_note("unknown", "x")
    assert msg.startswith("Error")
