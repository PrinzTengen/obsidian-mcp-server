from tools.folders import (
    create_folder,
    delete_folder,
    get_vault_tree,
    list_folder,
    move_folder,
)


def test_create_folder(tmp_vault):
    create_folder("test", "sub")
    assert (tmp_vault / "sub").is_dir()


def test_create_folder_nested(tmp_vault):
    create_folder("test", "a/b/c")
    assert (tmp_vault / "a" / "b" / "c").is_dir()


def test_create_existing_folder_returns_error(tmp_vault):
    create_folder("test", "x")
    assert create_folder("test", "x").startswith("Error")


def test_delete_empty_folder(tmp_vault):
    create_folder("test", "x")
    delete_folder("test", "x")
    assert not (tmp_vault / "x").exists()


def test_delete_non_empty_without_recursive_fails(tmp_vault):
    (tmp_vault / "x").mkdir()
    (tmp_vault / "x" / "note.md").write_text("x")
    msg = delete_folder("test", "x")
    assert "not empty" in msg


def test_delete_recursive(tmp_vault):
    (tmp_vault / "x").mkdir()
    (tmp_vault / "x" / "note.md").write_text("x")
    delete_folder("test", "x", recursive=True)
    assert not (tmp_vault / "x").exists()


def test_delete_missing_folder_returns_error(tmp_vault):
    assert delete_folder("test", "nope").startswith("Error")


def test_move_folder(tmp_vault):
    (tmp_vault / "src").mkdir()
    (tmp_vault / "src" / "f.md").write_text("x")
    move_folder("test", "src", "dst")
    assert not (tmp_vault / "src").exists()
    assert (tmp_vault / "dst" / "f.md").exists()


def test_list_folder_lists_files_and_dirs(tmp_vault):
    (tmp_vault / "a.md").write_text("x")
    (tmp_vault / "sub").mkdir()
    result = list_folder("test", "")
    names = {i["name"] for i in result["items"]}
    assert names == {"a.md", "sub"}
    types = {i["name"]: i["type"] for i in result["items"]}
    assert types["sub"] == "folder"
    assert types["a.md"] == "file"


def test_list_folder_missing_returns_error(tmp_vault):
    result = list_folder("test", "nope")
    assert "error" in result


def test_get_vault_tree_skips_hidden(tmp_vault):
    (tmp_vault / "visible.md").write_text("x")
    (tmp_vault / ".obsidian").mkdir()
    (tmp_vault / ".obsidian" / "workspace.json").write_text("{}")
    tree = get_vault_tree("test")
    child_names = {c["name"] for c in tree["children"]}
    assert "visible.md" in child_names
    assert ".obsidian" not in child_names


def test_get_vault_tree_root_name_is_vault(tmp_vault):
    tree = get_vault_tree("test")
    assert tree["name"] == "test"
    assert tree["type"] == "folder"
