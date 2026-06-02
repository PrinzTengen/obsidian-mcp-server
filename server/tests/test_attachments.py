import base64

from tools.attachments import delete_attachment, list_attachments, read_attachment


def test_list_attachments_filters_by_extension(tmp_vault):
    (tmp_vault / "image.png").write_bytes(b"PNGDATA")
    (tmp_vault / "doc.md").write_text("text")
    (tmp_vault / "audio.mp3").write_bytes(b"MP3")
    result = list_attachments("test")
    names = {r["name"] for r in result}
    assert names == {"image.png", "audio.mp3"}


def test_list_attachments_includes_size_and_ext(tmp_vault):
    (tmp_vault / "x.png").write_bytes(b"abc")
    result = list_attachments("test")
    entry = result[0]
    assert entry["extension"] == ".png"
    assert entry["size_bytes"] == 3


def test_list_attachments_skips_hidden_folders(tmp_vault):
    (tmp_vault / ".cache").mkdir()
    (tmp_vault / ".cache" / "hidden.png").write_bytes(b"x")
    (tmp_vault / "shown.png").write_bytes(b"x")
    paths = [r["path"] for r in list_attachments("test")]
    assert paths == ["shown.png"]


def test_read_attachment_returns_base64(tmp_vault):
    payload = b"binary-bytes\x00\xff"
    (tmp_vault / "f.png").write_bytes(payload)
    result = read_attachment("test", "f.png")
    assert base64.b64decode(result["data_base64"]) == payload
    assert result["size_bytes"] == len(payload)
    assert result["mime_type"] == "image/png"


def test_read_attachment_unsupported_type(tmp_vault):
    (tmp_vault / "f.txt").write_text("hi")
    result = read_attachment("test", "f.txt")
    assert "error" in result


def test_read_attachment_missing(tmp_vault):
    assert "error" in read_attachment("test", "nope.png")


def test_delete_attachment(tmp_vault):
    (tmp_vault / "f.png").write_bytes(b"x")
    delete_attachment("test", "f.png")
    assert not (tmp_vault / "f.png").exists()


def test_delete_attachment_unsupported_type(tmp_vault):
    (tmp_vault / "f.txt").write_text("hi")
    assert delete_attachment("test", "f.txt").startswith("Error")
    assert (tmp_vault / "f.txt").exists()
