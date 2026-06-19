import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP

import config as cfg
from tools.attachments import delete_attachment, list_attachments, read_attachment
from tools.folders import create_folder, delete_folder, get_vault_tree, list_folder, move_folder
from tools.metadata import get_backlinks, get_outlinks, read_frontmatter, write_frontmatter
from tools.notes import create_note, delete_note, move_note, read_note, update_note
from tools.search import find_notes, search_by_tag, search_notes

mcp = FastMCP("Obsidian MCP")


# ── Vault Management ──────────────────────────────────────────────────────────


@mcp.tool()
def list_vaults() -> dict:
    """List all configured Obsidian vaults.

    Call this at most once per conversation — the result is stable for the
    lifetime of the server process. Re-use the names you receive instead of
    re-querying.
    """
    vaults = cfg.list_vaults()
    if not vaults:
        return {"vaults": {}, "hint": "No vaults configured. Use 'add_vault' to add one."}
    return {"vaults": vaults}


@mcp.tool()
def add_vault(name: str, path: str) -> str:
    """Add an Obsidian vault to the configuration.

    Args:
        name: Short name for the vault (e.g. 'Personal', 'Work')
        path: Absolute path to the vault folder (e.g. C:/Users/.../Obsidian/Personal)
    """
    from pathlib import Path as P

    vault_path = P(path)
    if not vault_path.exists():
        return f"Error: Path does not exist: {path}"
    if not vault_path.is_dir():
        return f"Error: Path is not a folder: {path}"
    cfg.add_vault(name, str(vault_path.resolve()))
    return f"Vault added: '{name}' -> {path}"


@mcp.tool()
def remove_vault(name: str) -> str:
    """Remove a vault from the configuration (does not delete any files).

    Args:
        name: Name of the vault to remove
    """
    vaults = cfg.list_vaults()
    if name not in vaults:
        return f"Error: Vault '{name}' not found. Available: {list(vaults.keys())}"
    cfg.remove_vault(name)
    return f"Vault removed: '{name}'"


# ── Notes ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def create_note_tool(
    vault: str, path: str, content: str = "", frontmatter: dict | None = None
) -> str:
    """Create a new Markdown note in the vault.

    Args:
        vault: Vault name
        path: Path to the note relative to the vault root (e.g. 'Projects/Ideas/MyIdea')
        content: Markdown content of the note
        frontmatter: YAML frontmatter as a dictionary (e.g. {"tags": ["ai", "project"]})
    """
    return create_note(vault, path, content, frontmatter)


@mcp.tool()
def read_note_tool(vault: str, path: str) -> dict:
    """Read a note — returns content and frontmatter.

    Args:
        vault: Vault name
        path: Path to the note relative to the vault root
    """
    return read_note(vault, path)


@mcp.tool()
def update_note_tool(
    vault: str, path: str, content: str | None = None, frontmatter: dict | None = None
) -> str:
    """Update an existing note (content and/or frontmatter).

    Args:
        vault: Vault name
        path: Path to the note
        content: New Markdown content (None = keep unchanged)
        frontmatter: Frontmatter updates as a dictionary (merged into existing)
    """
    return update_note(vault, path, content, frontmatter)


@mcp.tool()
def delete_note_tool(vault: str, path: str) -> str:
    """Permanently delete a note.

    Args:
        vault: Vault name
        path: Path to the note
    """
    return delete_note(vault, path)


@mcp.tool()
def move_note_tool(vault: str, from_path: str, to_path: str) -> str:
    """Move or rename a note.

    Args:
        vault: Vault name
        from_path: Current path of the note
        to_path: New path of the note
    """
    return move_note(vault, from_path, to_path)


# ── Folders ───────────────────────────────────────────────────────────────────


@mcp.tool()
def create_folder_tool(vault: str, path: str) -> str:
    """Create a new folder in the vault.

    Args:
        vault: Vault name
        path: Path of the new folder relative to the vault root
    """
    return create_folder(vault, path)


@mcp.tool()
def delete_folder_tool(vault: str, path: str, recursive: bool = False) -> str:
    """Delete a folder.

    Args:
        vault: Vault name
        path: Path to the folder
        recursive: True = delete including all contents, False = only empty folders
    """
    return delete_folder(vault, path, recursive)


@mcp.tool()
def move_folder_tool(vault: str, from_path: str, to_path: str) -> str:
    """Move or rename a folder.

    Args:
        vault: Vault name
        from_path: Current path
        to_path: New path
    """
    return move_folder(vault, from_path, to_path)


@mcp.tool()
def list_folder_tool(vault: str, path: str = "") -> dict:
    """List the contents of a folder (one level, not recursive).

    Args:
        vault: Vault name
        path: Path to the folder (empty = vault root)
    """
    return list_folder(vault, path)


@mcp.tool()
def get_vault_tree_tool(vault: str) -> dict:
    """Show the complete directory structure of the vault as a tree.

    Call this once per turn at most — the result is cached and only
    re-computed when the vault actually changes. Keep the tree in mind
    while planning subsequent reads instead of re-fetching it.

    Args:
        vault: Vault name
    """
    return get_vault_tree(vault)


# ── Search ────────────────────────────────────────────────────────────────────


@mcp.tool()
def search_notes_tool(
    vault: str, query: str, folder: str = "", case_sensitive: bool = False
) -> list:
    """Full-text search across all notes in the vault.

    Backed by an in-memory index that is incrementally synced with disk on
    every call, so results reflect both MCP-side edits and edits made
    externally in Obsidian. The index covers note body text — not YAML
    frontmatter values, which are matched separately via tag search.

    Args:
        vault: Vault name
        query: Search term
        folder: Only search in this subfolder (empty = entire vault)
        case_sensitive: Whether the search is case-sensitive
    """
    return search_notes(vault, query, folder, case_sensitive)


@mcp.tool()
def find_notes_tool(vault: str, query: str, limit: int = 20) -> list:
    """Quickly find a note by name/title — fuzzy and typo-tolerant.

    The fastest way to locate a note when you roughly know its name. Matches
    against filename, frontmatter `title`, and folder path, tolerates typos
    (e.g. 'projkt' finds 'Projekt'), and returns the best matches ranked by
    relevance with a `score`. Runs off the in-memory index, so it's instant
    even on large vaults. For searching inside note bodies use `search_notes`.

    Args:
        vault: Vault name
        query: Approximate note name or title
        limit: Maximum number of results to return (default 20)
    """
    return find_notes(vault, query, limit)


@mcp.tool()
def search_by_tag_tool(vault: str, tag: str) -> list:
    """Find all notes with a specific tag (frontmatter + inline tags).

    Args:
        vault: Vault name
        tag: Tag without # (e.g. 'project') or with # ('#project')
    """
    return search_by_tag(vault, tag)


# ── Metadata ──────────────────────────────────────────────────────────────────


@mcp.tool()
def read_frontmatter_tool(vault: str, path: str) -> dict:
    """Read the YAML frontmatter of a note.

    Args:
        vault: Vault name
        path: Path to the note
    """
    return read_frontmatter(vault, path)


@mcp.tool()
def write_frontmatter_tool(vault: str, path: str, frontmatter: dict, merge: bool = True) -> str:
    """Write or update the YAML frontmatter of a note.

    Args:
        vault: Vault name
        path: Path to the note
        frontmatter: New frontmatter data as a dictionary
        merge: True = keep existing fields and add new ones, False = replace completely
    """
    return write_frontmatter(vault, path, frontmatter, merge)


@mcp.tool()
def get_backlinks_tool(vault: str, path: str) -> list:
    """Find all notes that link to this note (backlinks).

    Args:
        vault: Vault name
        path: Path to the target note
    """
    return get_backlinks(vault, path)


@mcp.tool()
def get_outlinks_tool(vault: str, path: str) -> list:
    """Extract all links from a note (wikilinks + markdown links).

    Args:
        vault: Vault name
        path: Path to the note
    """
    return get_outlinks(vault, path)


# ── Attachments ───────────────────────────────────────────────────────────────


@mcp.tool()
def list_attachments_tool(vault: str, folder: str = "") -> list:
    """List all attachments (images, PDFs, etc.) in the vault.

    Args:
        vault: Vault name
        folder: Only search in this subfolder (empty = entire vault)
    """
    return list_attachments(vault, folder)


@mcp.tool()
def read_attachment_tool(vault: str, path: str) -> dict:
    """Read an attachment as Base64-encoded data.

    Args:
        vault: Vault name
        path: Path to the attachment file
    """
    return read_attachment(vault, path)


@mcp.tool()
def delete_attachment_tool(vault: str, path: str) -> str:
    """Permanently delete an attachment.

    Args:
        vault: Vault name
        path: Path to the attachment file
    """
    return delete_attachment(vault, path)


# ── Entry Point ───────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Obsidian MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="sse",
        help="Transport protocol (default: sse)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host address for SSE (default: 127.0.0.1)"
    )
    parser.add_argument("--port", type=int, default=3333, help="Port for SSE (default: 3333)")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
