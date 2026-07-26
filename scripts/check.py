#!/usr/bin/env python3
"""
Repo hygiene checks for madugong-skill. Run via `npm test` or directly.

1. Skill package structure: required files exist, SKILL.md has frontmatter,
   references mentioned in SKILL.md actually exist on disk.
2. Publish sync: regenerates publish/ and fails if the committed copy drifted
   (the regenerated files are left in place — just commit them).
"""

import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_SOURCE = REPO_ROOT / ".claude" / "skills" / "madugong-perspective"

errors = []


def check_structure():
    for name in ("SKILL.md", "fewshots.md"):
        if not (SKILL_SOURCE / name).exists():
            errors.append(f"missing required file: {SKILL_SOURCE / name}")

    skill_md = SKILL_SOURCE / "SKILL.md"
    if skill_md.exists():
        text = skill_md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            errors.append("SKILL.md is missing YAML frontmatter")
        # every references/<file> mentioned in the prompt must exist
        for ref in set(re.findall(r"references/[\w.-]+\.md", text)):
            if not (SKILL_SOURCE / ref).exists():
                errors.append(f"SKILL.md mentions {ref} but the file does not exist")


def snapshot_publish():
    publish_dir = REPO_ROOT / "publish"
    if not publish_dir.is_dir():
        return {}
    return {
        p.relative_to(publish_dir).as_posix(): p.read_bytes()
        for p in publish_dir.rglob("*") if p.is_file()
    }


def check_publish_sync():
    before = snapshot_publish()
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "publish.py")],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        errors.append(f"publish.py failed:\n{result.stderr}")
        return
    after = snapshot_publish()
    stale = sorted(
        path for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    )
    if stale:
        errors.append(
            "publish/ was out of sync with the skill source. "
            "It has been regenerated — review and commit:\n  " + "\n  ".join(stale)
        )


def main():
    check_structure()
    check_publish_sync()
    if errors:
        print("FAIL")
        for e in errors:
            print(f"- {e}")
        sys.exit(1)
    print("OK: structure + publish sync")


if __name__ == "__main__":
    main()
