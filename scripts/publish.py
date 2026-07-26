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


DISCLAIMER = (
    "<!-- madugong-perspective -->\n"
    "<!-- Paste this file into any AI chat to activate the Ma Dugong persona. -->\n"
    "<!-- For Claude Code installation, use the release zip instead. -->\n"
    "<!--\n"
    "  免责声明：本文件为 AI 角色扮演提示词，基于马前卒（任冲昊）截至 2026 年 4 月的\n"
    "  公开内容提炼，属于风格模拟，不是马前卒本人，不代表其本人观点，\n"
    "  不保证结论的正确性和时效性。禁止用于冒充本人或商业化用途。\n"
    "-->\n\n"
)


def merge_to_single_md():
    """Merge SKILL.md + references + fewshots.md into a single madugong.md."""
    skill_md = SKILL_SOURCE / "SKILL.md"
    fewshots_md = SKILL_SOURCE / "fewshots.md"

    if not skill_md.exists():
        print(f"Error: {skill_md} not found", file=sys.stderr)
        sys.exit(1)
    if not fewshots_md.exists():
        print(f"Error: {fewshots_md} not found", file=sys.stderr)
        sys.exit(1)

    parts = [strip_frontmatter(skill_md.read_text(encoding="utf-8"))]

    references_dir = SKILL_SOURCE / "references"
    if references_dir.is_dir():
        for ref in sorted(references_dir.glob("*.md")):
            parts.append(strip_frontmatter(ref.read_text(encoding="utf-8")))

    parts.append(fewshots_md.read_text(encoding="utf-8"))

    merged = DISCLAIMER + "\n\n".join(part.strip("\n") for part in parts) + "\n"

    MERGED_OUTPUT.write_text(merged, encoding="utf-8")
    print(f"Merged to {MERGED_OUTPUT}")


def main():
    print("=== Publish madugong-perspective ===")
    sync_skill_to_publish()
    merge_to_single_md()
    print("Done.")


if __name__ == "__main__":
    main()
