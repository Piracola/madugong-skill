#!/usr/bin/env python3
"""
Build eval/heldout.jsonl from the local corpus.

Reads eval/selection.tsv (bucket<TAB>filename<TAB>topic, one per line, '#' comments
allowed), pulls each file from docs/睡前消息-知乎内容合集/, and writes one JSON
record per question: {id, bucket, topic, question, reference, source}.

The corpus (docs/) is not committed to git; heldout.jsonl is, so the eval set
stays usable for people without the corpus. Re-run this only when selection.tsv
changes and the corpus is present locally.
"""

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS = REPO_ROOT / "docs" / "睡前消息-知乎内容合集"
SELECTION = REPO_ROOT / "eval" / "selection.tsv"
OUTPUT = REPO_ROOT / "eval" / "heldout.jsonl"


def main():
    if not CORPUS.is_dir():
        sys.exit(f"corpus not found: {CORPUS} (docs/ is local-only)")
    if not SELECTION.exists():
        sys.exit(f"selection list not found: {SELECTION}")

    records, missing = [], []
    for line in SELECTION.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            bucket, filename, topic = line.split("\t")
        except ValueError:
            sys.exit(f"bad selection line (need 3 tab-separated fields): {line!r}")
        path = CORPUS / filename
        if not path.exists():
            missing.append(filename)
            continue
        text = path.read_text(encoding="utf-8").strip()
        lines = text.splitlines()
        if not lines or not lines[0].startswith("#"):
            missing.append(f"{filename} (no '# question' title line)")
            continue
        question = lines[0].lstrip("#").strip()
        reference = "\n".join(lines[1:]).strip()
        if len(reference) < 2:
            missing.append(f"{filename} (empty answer body)")
            continue
        records.append({
            "id": f"q{len(records) + 1:03d}",
            "bucket": bucket,
            "topic": topic,
            "question": question,
            "reference": reference,
            "source": filename,
        })

    if missing:
        print("skipped entries:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)

    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    buckets = {}
    for r in records:
        buckets[r["bucket"]] = buckets.get(r["bucket"], 0) + 1
    print(f"wrote {len(records)} records to {OUTPUT} ({buckets})")


if __name__ == "__main__":
    main()
