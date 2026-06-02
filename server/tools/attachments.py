import base64
import mimetypes
from pathlib import Path

from vault_manager import VaultError, get_vault, resolve_path

ATTACHMENT_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".mp3",
    ".mp4",
    ".wav",
    ".svg",
    ".excalidraw",
}


def _is_attachment(path: Path) -> bool:
    return path.suffix.lower() in ATTACHMENT_EXTENSIONS


def list_attachments(vault: str, folder: str = "") -> list:
    try:
        vault_path = get_vault(vault)
        base = resolve_path(vault_path, folder) if folder else vault_path.resolve()
        if not base.exists():
            return [{"error": f"Ordner nicht gefunden: {folder}"}]
        results = []
        for item in base.rglob("*"):
            if item.is_file() and _is_attachment(item):
                if any(part.startswith(".") for part in item.parts):
                    continue
                rel = str(item.relative_to(vault_path)).replace("\\", "/")
                results.append(
                    {
                        "path": rel,
                        "name": item.name,
                        "extension": item.suffix.lower(),
                        "size_bytes": item.stat().st_size,
                    }
                )
        results.sort(key=lambda r: r["path"])
        return results
    except VaultError as e:
        return [{"error": str(e)}]


def read_attachment(vault: str, path: str) -> dict:
    try:
        vault_path = get_vault(vault)
        file_path = resolve_path(vault_path, path)
        if not file_path.exists():
            return {"error": f"File not found: {path}"}
        if not _is_attachment(file_path):
            return {"error": f"Unsupported file type: {file_path.suffix}"}
        data = file_path.read_bytes()
        mime, _ = mimetypes.guess_type(str(file_path))
        return {
            "path": path,
            "mime_type": mime or "application/octet-stream",
            "data_base64": base64.b64encode(data).decode("ascii"),
            "size_bytes": len(data),
        }
    except VaultError as e:
        return {"error": str(e)}


def delete_attachment(vault: str, path: str) -> str:
    try:
        vault_path = get_vault(vault)
        file_path = resolve_path(vault_path, path)
        if not file_path.exists():
            return f"Error: File not found: {path}"
        if not _is_attachment(file_path):
            return f"Error: Unsupported file type: {file_path.suffix}"
        file_path.unlink()
        return f"Attachment deleted: {path}"
    except VaultError as e:
        return f"Error: {e}"
