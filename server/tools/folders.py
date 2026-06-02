import shutil
from pathlib import Path

from vault_manager import VaultError, ensure_parent, get_vault, resolve_path


def create_folder(vault: str, path: str) -> str:
    try:
        vault_path = get_vault(vault)
        folder = resolve_path(vault_path, path)
        if folder.exists():
            return f"Error: Folder already exists: {path}"
        folder.mkdir(parents=True)
        return f"Folder created: {path}"
    except VaultError as e:
        return f"Error: {e}"


def delete_folder(vault: str, path: str, recursive: bool = False) -> str:
    try:
        vault_path = get_vault(vault)
        folder = resolve_path(vault_path, path)
        if not folder.exists():
            return f"Error: Folder not found: {path}"
        if not folder.is_dir():
            return f"Error: Path is not a folder: {path}"
        if recursive:
            shutil.rmtree(folder)
        else:
            try:
                folder.rmdir()
            except OSError:
                return "Error: Folder is not empty. Use recursive=True to delete with content."
        return f"Folder deleted: {path}"
    except VaultError as e:
        return f"Error: {e}"


def move_folder(vault: str, from_path: str, to_path: str) -> str:
    try:
        vault_path = get_vault(vault)
        src = resolve_path(vault_path, from_path)
        dst = resolve_path(vault_path, to_path)
        if not src.exists():
            return f"Error: Folder not found: {from_path}"
        if dst.exists():
            return f"Error: Destination already exists: {to_path}"
        ensure_parent(dst)
        shutil.move(str(src), str(dst))
        return f"Folder moved: {from_path} -> {to_path}"
    except VaultError as e:
        return f"Error: {e}"


def list_folder(vault: str, path: str = "") -> dict:
    try:
        vault_path = get_vault(vault)
        folder = resolve_path(vault_path, path) if path else vault_path
        if not folder.exists():
            return {"error": f"Folder not found: {path}"}
        if not folder.is_dir():
            return {"error": f"Path is not a folder: {path}"}
        items = []
        for item in sorted(folder.iterdir()):
            rel = str(item.relative_to(vault_path)).replace("\\", "/")
            if item.is_dir():
                items.append({"name": item.name, "path": rel, "type": "folder"})
            else:
                items.append(
                    {
                        "name": item.name,
                        "path": rel,
                        "type": "file",
                        "extension": item.suffix,
                    }
                )
        return {"path": path or "/", "items": items}
    except VaultError as e:
        return {"error": str(e)}


def get_vault_tree(vault: str) -> dict:
    try:
        vault_path = get_vault(vault)

        def build_tree(folder: Path) -> dict:
            result = {"name": folder.name, "type": "folder", "children": []}
            folders = []
            files = []
            for item in sorted(folder.iterdir()):
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    folders.append(build_tree(item))
                else:
                    files.append(
                        {
                            "name": item.name,
                            "type": "file",
                            "extension": item.suffix,
                        }
                    )
            result["children"] = folders + files
            return result

        tree = build_tree(vault_path)
        tree["name"] = vault
        return tree
    except VaultError as e:
        return {"error": str(e)}
