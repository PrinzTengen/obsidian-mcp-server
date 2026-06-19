# Obsidian MCP

Give AI assistants direct access to your Obsidian vaults via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io).

**Supported clients:** Claude Desktop · Claude Code CLI · VS Code (Continue, Cline, Copilot) · OpenWebUI · AnythingLLM · n8n

**23 Tools:** Create/read/edit/delete notes · Manage folders · Fuzzy & full-text search · Tags & backlinks · Attachments · Multi-vault support

---

## Table of Contents

- [Manual Installation](#manual-installation)
- [Installation via BRAT](#installation-via-brat)
- [Connect Claude Desktop](#connect-claude-desktop)
- [Connect Claude Code CLI](#connect-claude-code-cli)
- [Adding Vaults](#adding-vaults)
- [All MCP Tools](#all-mcp-tools)
- [Troubleshooting](#troubleshooting)

---

## Manual Installation

### 1. Download the plugin

Go to the [Releases page](https://github.com/maxnoelp/obsidian-mcp-server/releases/latest) and download **`obsidian-mcp-windows.zip`**.

### 2. Extract into your Obsidian vault

Unzip the archive. You will get a folder `obsidian-mcp/` with the following contents:

```
obsidian-mcp/
├── main.js
├── manifest.json
├── styles.css
└── bin/
    └── obsidian-mcp-server.exe
```

Copy this folder to:

```
<Your Vault>\.obsidian\plugins\obsidian-mcp\
```

**Example:**
```
C:\Users\Name\Documents\Obsidian\MyVault\.obsidian\plugins\obsidian-mcp\
```

### 3. Enable the plugin in Obsidian

1. Open Obsidian
2. Go to **Settings → Community Plugins**
3. If not already enabled: click **"Turn on community plugins"**
4. Under **Installed Plugins** → **Obsidian MCP** → enable the toggle

The server starts automatically. The status bar at the bottom will show `MCP :3333`.

---

## Installation via BRAT

[BRAT](https://github.com/TfTHacker/obsidian42-brat) is an Obsidian plugin that installs beta plugins directly from GitHub and keeps them updated automatically.

### 1. Install BRAT

1. Obsidian → Settings → Community Plugins → Browse
2. Search for **"BRAT"** → Install → Enable

### 2. Add Obsidian MCP via BRAT

1. **Settings → BRAT → "Add Beta Plugin"**
2. Enter the GitHub URL:
   ```
   https://github.com/maxnoelp/obsidian-mcp-server
   ```
3. Click **"Add Plugin"** — BRAT will automatically download the latest release

### 3. Enable the plugin

Settings → Community Plugins → **Obsidian MCP** → enable the toggle

BRAT will automatically update the plugin whenever a new version is released.

---

## Connect Claude Desktop

Claude Desktop launches the server **itself** in the background — the Obsidian plugin does **not** need to be running.

### 1. Open the config file

```
%APPDATA%\Claude\claude_desktop_config.json
```

> Windows: `C:\Users\<Name>\AppData\Roaming\Claude\claude_desktop_config.json`

### 2. Add the MCP server

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "C:\\Users\\<Name>\\<Vault>\\.obsidian\\plugins\\obsidian-mcp\\bin\\obsidian-mcp-server.exe",
      "args": ["--transport", "stdio"]
    }
  }
}
```

Adjust the path to match the actual location of `obsidian-mcp-server.exe` on your system.

### 3. Restart Claude Desktop

After restarting, a **hammer icon** will appear in the top-left of the chat — this confirms the MCP tools are available.

### 4. Add your vault

On first start no vault is configured yet. Simply tell Claude:

```
Add my vault at C:\Users\<Name>\Documents\Obsidian\MyVault
```

Claude will automatically call the `add_vault` tool.

### 5. Test it

```
Show me all configured vaults
List the contents of my vault
Create a note called "Test" with the content "Hello World"
```

---

## Connect Claude Code CLI

The Obsidian plugin runs the server in SSE mode on port 3333. Claude Code connects to it directly.

### Requirement

Obsidian must be open with the plugin enabled — the server then runs automatically in the background.

### Register the MCP server (once)

```bash
claude mcp add --transport sse obsidian http://127.0.0.1:3333/sse
```

### Test it

```bash
claude
```

Then in the chat:
```
Show me all vaults
Search my vault for "project idea"
```

### Alternative: manual config

In `.claude/mcp.json` in your project folder (or globally):

```json
{
  "mcpServers": {
    "obsidian": {
      "transport": "sse",
      "url": "http://127.0.0.1:3333/sse"
    }
  }
}
```

---

## Adding Vaults

### Via the Obsidian plugin (recommended)

1. Obsidian → Settings → **Obsidian MCP**
2. Under **Vaults** → click **"Add current vault"**

The currently open vault is detected automatically.

### Via Claude

```
Add the vault "Work" at C:\Users\Name\Documents\Obsidian\Work
```

### Via config file

```
%USERPROFILE%\.obsidian-mcp\config.json
```

```json
{
  "vaults": {
    "Personal": "C:\\Users\\Name\\Documents\\Obsidian\\Personal",
    "Work": "C:\\Users\\Name\\Documents\\Obsidian\\Work"
  }
}
```

---

## All MCP Tools

| Category | Tool | Description |
|----------|------|-------------|
| **Vaults** | `list_vaults` | List all configured vaults |
| | `add_vault` | Add a vault |
| | `remove_vault` | Remove a vault |
| **Notes** | `create_note_tool` | Create a new note |
| | `read_note_tool` | Read a note (content + frontmatter) |
| | `update_note_tool` | Update a note |
| | `delete_note_tool` | Delete a note |
| | `move_note_tool` | Move or rename a note |
| **Folders** | `create_folder_tool` | Create a folder |
| | `delete_folder_tool` | Delete a folder |
| | `move_folder_tool` | Move or rename a folder |
| | `list_folder_tool` | List folder contents |
| | `get_vault_tree_tool` | Show the full vault structure |
| **Search** | `find_notes_tool` | Fast fuzzy lookup by note name/title (typo-tolerant) |
| | `search_notes_tool` | Full-text search |
| | `search_by_tag_tool` | Search by tag |
| **Metadata** | `read_frontmatter_tool` | Read YAML frontmatter |
| | `write_frontmatter_tool` | Write YAML frontmatter |
| | `get_backlinks_tool` | Get backlinks of a note |
| | `get_outlinks_tool` | Get all links from a note |
| **Attachments** | `list_attachments_tool` | List attachments |
| | `read_attachment_tool` | Read attachment as Base64 |
| | `delete_attachment_tool` | Delete an attachment |

---

## Troubleshooting

**Server does not start**
→ Settings → Obsidian MCP → click **"Open Log"** — the log file shows the exact error.

**Port 3333 already in use**
→ Settings → Obsidian MCP → change port to e.g. `3334` → restart.

**Claude Desktop shows no tools**
→ Check the path in `claude_desktop_config.json` (use double backslashes `\\`).
→ Fully restart Claude Desktop (don't just close the window).
