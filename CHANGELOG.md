# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Alle nennenswerten Änderungen an diesem Projekt werden in dieser Datei
dokumentiert (Format nach *Keep a Changelog*, Versionierung nach *SemVer*).

## [0.4.0] - 2026-06-19

### Added

**English**

- **New `find_notes` tool — fast, fuzzy, typo-tolerant note lookup by
  name/title.** Locates a note when you only roughly remember its name. It
  matches against the filename, the frontmatter `title`, and the folder path,
  tolerates typos (e.g. `projkt` finds `Projekt`), and returns the best matches
  ranked by a relevance `score`, capped by `limit` (default 20). Runs entirely
  off the in-memory index with no disk reads, so it stays instant on large
  vaults. Ranking is layered: exact match > prefix > substring > in-order
  subsequence, with a similarity ratio as the typo-tolerant floor. Use
  `find_notes` to jump to a note by name; use `search_notes` for full-text body
  search.

**Deutsch**

- **Neues Tool `find_notes` — schnelles, fuzzy/tippfehler-tolerantes Finden von
  Notizen nach Name/Titel.** Findet eine Notiz, wenn man ihren Namen nur
  ungefähr kennt. Es matcht gegen Dateiname, Frontmatter-`title` und Ordnerpfad,
  verzeiht Tippfehler (z.B. `projkt` findet `Projekt`) und liefert die besten
  Treffer nach einem Relevanz-`score` sortiert, begrenzt durch `limit`
  (Standard 20). Läuft komplett über den In-Memory-Index ohne Disk-Zugriffe und
  bleibt damit auch bei großen Vaults sofort schnell. Das Ranking ist
  gestaffelt: exakt > Präfix > Teilstring > Teilfolge in Reihenfolge, mit einer
  Ähnlichkeits-Ratio als tippfehler-toleranter Untergrenze. `find_notes` zum
  Anspringen einer Notiz per Name; `search_notes` für die Volltextsuche im
  Notiz-Inhalt.

### Performance

**English**

- **Backlinks now use the in-memory index** instead of reading every note from
  disk on each call. `get_backlinks` previously walked the whole vault with
  `rglob` and ran a regex over every file on every invocation; it now scans the
  already-parsed `outlinks` held in the index. On large vaults this turns a
  multi-second, disk-bound operation into an in-memory lookup.
- **Index sync rewritten on `os.scandir`.** `VaultIndex.build` and
  `ensure_fresh` now walk the vault with an explicit `scandir` stack instead of
  `Path.rglob` + a separate `stat()` per file. Directory entries carry cached
  `st_mtime`/`st_size` (notably on Windows), so the periodic freshness sweep —
  which runs on most tool calls — no longer issues an extra `stat()` syscall per
  note, and the per-file `Path.resolve()` call was removed.
- **Hidden directories are pruned during traversal.** `.obsidian/`, `.git/`,
  `.trash/` and other dot-folders are no longer descended into at all, instead
  of being walked and then filtered out afterwards. This avoids scanning large
  plugin/workspace caches.
- **Full-text search skips non-matching notes cheaply.** `search_notes` now does
  a single whole-document membership test before the per-line `splitlines()` +
  regex pass, so notes that cannot match are skipped without line-by-line work.
- **Writes no longer parse the same file twice.** After `create_note`,
  `update_note` and `write_frontmatter` write a file, they hand the
  already-parsed content/frontmatter straight to the index
  (`registry.notify_change(..., content=..., frontmatter=...)` →
  `VaultIndex.set_note`) instead of triggering a fresh `frontmatter.load` of the
  file just written.

**Deutsch**

- **Backlinks nutzen jetzt den In-Memory-Index** statt bei jedem Aufruf alle
  Notizen von der Platte zu lesen. `get_backlinks` lief vorher per `rglob` über
  den gesamten Vault und führte pro Datei eine Regex aus; jetzt werden die
  bereits geparsten `outlinks` aus dem Index gescannt. Bei großen Vaults wird
  aus einer sekundenlangen, plattengebundenen Operation ein RAM-Lookup.
- **Index-Synchronisation auf `os.scandir` umgestellt.** `VaultIndex.build` und
  `ensure_fresh` durchlaufen den Vault mit einem expliziten `scandir`-Stack
  statt `Path.rglob` + separatem `stat()` pro Datei. Die Verzeichniseinträge
  liefern gecachte `st_mtime`/`st_size` (vor allem unter Windows), wodurch der
  periodische Freshness-Sweep — der bei fast jedem Tool-Aufruf läuft — keinen
  zusätzlichen `stat()`-Syscall pro Notiz mehr braucht; der `Path.resolve()`-
  Aufruf pro Datei entfällt ebenfalls.
- **Versteckte Verzeichnisse werden beim Traversieren übersprungen.**
  `.obsidian/`, `.git/`, `.trash/` und andere Punkt-Ordner werden gar nicht
  mehr betreten, statt durchlaufen und nachträglich herausgefiltert zu werden.
  Das vermeidet das Scannen großer Plugin-/Workspace-Caches.
- **Volltextsuche überspringt Nicht-Treffer günstig.** `search_notes` macht jetzt
  einen einzigen Membership-Test über das ganze Dokument, bevor `splitlines()` +
  Regex pro Zeile laufen — Notizen ohne mögliche Treffer werden ohne
  zeilenweise Arbeit übersprungen.
- **Schreibvorgänge parsen dieselbe Datei nicht mehr doppelt.** Nach dem
  Schreiben übergeben `create_note`, `update_note` und `write_frontmatter` den
  bereits geparsten Inhalt/Frontmatter direkt an den Index
  (`registry.notify_change(..., content=..., frontmatter=...)` →
  `VaultIndex.set_note`), statt ein erneutes `frontmatter.load` der gerade
  geschriebenen Datei auszulösen.

### Notes / Hinweise

- No public tool signatures changed; all 110 server tests pass unchanged.
- Es haben sich keine öffentlichen Tool-Signaturen geändert; alle 110
  Server-Tests laufen unverändert grün.

## [0.3.0]

- Introduced the `VaultIndex` registry for cached note metadata and enhanced
  note operations (see release notes for v0.3.0).
- Einführung der `VaultIndex`-Registry für gecachte Notiz-Metadaten sowie
  verbesserte Notiz-Operationen (siehe Release Notes zu v0.3.0).
