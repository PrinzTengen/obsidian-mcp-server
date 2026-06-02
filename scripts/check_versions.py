#!/usr/bin/env python3
"""Verify that all version strings in the repo agree.

Checks that these files declare the same version:
  - manifest.json           (root, for BRAT)
  - plugin/manifest.json     (Obsidian plugin manifest)
  - plugin/package.json      (npm metadata)

Usage:
  python scripts/check_versions.py            # only consistency between files
  python scripts/check_versions.py v0.2.0     # also require all == 0.2.0 (tag)

Exits 0 if everything matches, 1 otherwise.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILES = {
    "manifest.json": ROOT / "manifest.json",
    "plugin/manifest.json": ROOT / "plugin" / "manifest.json",
    "plugin/package.json": ROOT / "plugin" / "package.json",
}


def read_version(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["version"]


def main() -> int:
    expected = None
    if len(sys.argv) > 1:
        expected = sys.argv[1].lstrip("v")

    versions = {name: read_version(path) for name, path in FILES.items()}

    for name, version in versions.items():
        print(f"  {name}: {version}")

    unique = set(versions.values())
    if len(unique) != 1:
        print(f"ERROR: version mismatch between files: {versions}", file=sys.stderr)
        return 1

    actual = unique.pop()

    if expected is not None and actual != expected:
        print(
            f"ERROR: tag is '{expected}' but files declare '{actual}'",
            file=sys.stderr,
        )
        return 1

    target = expected or actual
    print(f"OK: all versions agree on {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
