#!/usr/bin/env python3
"""
Release publish script for madugong-perspective skill.

Run in GitHub Actions when creating a release. Does two things:
1. Copies .claude/skills/madugong-perspective to publish/ (Claude Code install source)
2. Merges SKILL.md + fewshots.md into a single madugong.md (release artifact)
"""

import os
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_SOURCE = REPO_ROOT / ".claude" / "skills" / "madugong-perspective"
PUBLISH_DIR = REPO_ROOT / "publish" / "madugong-perspective"
MERGED_OUTPUT = REPO_ROOT / "publish" / "madugong.md"


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from the beginning of a file."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].lstrip("\n")
    return text


def sync_skill_to_publish():
    """Copy the skill folder to publish/ for Claude Code installation."""
    if not SKILL_SOURCE.is_dir():
        print(f"Error: skill source not found: {SKILL_SOURCE}", file=sys.stderr)
        sys.exit(1)

    if PUBLISH_DIR.exists():
        shutil.rmtree(PUBLISH_DIR)
    PUBLISH_DIR.mkdir(parents=True)

    for entry in SKILL_SOURCE.iterdir():
        dest = PUBLISH_DIR / entry.name
        if entry.is_dir():
            shutil.copytree(entry, dest)
        else:
            shutil.copy2(entry, dest)

    print(f"Synced skill to {PUBLISH_DIR}")


def merge_to_single_md():
    """Merge SKILL.md + fewshots.md into a single madugong.md for release."""
    skill_md = SKILL_SOURCE / "SKILL.md"
    fewshots_md = SKILL_SOURCE / "fewshots.md"

    if not skill_md.exists():
        print(f"Error: {skill_md} not found", file=sys.stderr)
        sys.exit(1)
    if not fewshots_md.exists():
        print(f"Error: {fewshots_md} not found", file=sys.stderr)
        sys.exit(1)

    skill_text = strip_frontmatter(skill_md.read_text(encoding="utf-8"))
    fewshots_text = fewshots_md.read_text(encoding="utf-8")

    merged = (
        "<!-- madugong-perspective -->\n"
        "<!-- Paste this file into any AI chat to activate the Ma Dugong persona. -->\n"
        "<!-- For Claude Code installation, use the release zip instead. -->\n\n"
        f"{skill_text}\n\n"
        f"{fewshots_text}"
    )

    MERGED_OUTPUT.write_text(merged, encoding="utf-8")
    print(f"Merged to {MERGED_OUTPUT}")


def main():
    print("=== Publish madugong-perspective ===")
    sync_skill_to_publish()
    merge_to_single_md()
    print("Done.")


if __name__ == "__main__":
    main()
