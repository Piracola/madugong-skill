#!/usr/bin/env python3
"""
Style-distribution metrics for the madugong eval loop.

Computes, for a set of texts, the measurable side of the skill's style rules:
sentence-rhythm asymmetry, hedging-word rate, AI-template phrase hits, number
density, and how the answers open and close. Run it on the held-out reference
answers and on model outputs, and compare the two columns — the model column
should converge toward the reference column as the skill improves.

Usage:
  python scripts/style_stats.py eval/heldout.jsonl --field reference
  python scripts/style_stats.py outputs.jsonl --field answer
  python scripts/style_stats.py outputs.jsonl --field answer --ref eval/heldout.jsonl
"""

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

HEDGES = [
    "也许", "或许", "不可否认", "我个人认为", "在一定程度上", "综上所述",
    "总而言之", "总的来说", "需要注意的是", "值得注意的是", "客观来说",
    "不得不说", "某种意义上",
]

# The blocklist from fewshots.md 输出自检, as detectable patterns.
TEMPLATES = [
    ("不是……而是……", re.compile(r"不是[^。！？\n]{1,24}而是")),
    ("算账句式", re.compile(r"算[一笔个]?[经济]{0,2}账|这笔账")),
    ("我们来/让我们", re.compile(r"(我们来|让我们)")),
    ("从……角度", re.compile(r"从[^。！？\n]{1,12}角度")),
    ("这是X问题不是Y问题", re.compile(r"这不?是[^。！？\n]{1,12}问题[，,][^。！？\n]{0,4}[是而]")),
    ("工程学措辞", re.compile(r"工程学|工程思维")),
]

CLOSING_UPLIFT = re.compile(r"(希望|总之|综上|期待|让我们|未来会更|相信)")
SENT_SPLIT = re.compile(r"[。！？!?…]+")
NUM = re.compile(r"\d[\d,.%]*")


def load_texts(path, field):
    texts = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if field not in obj:
            sys.exit(f"field '{field}' not found in record: {list(obj)}")
        texts.append(obj[field])
    if not texts:
        sys.exit(f"no records in {path}")
    return texts


def analyze(texts):
    sent_lens, para_counts, hedge_hits, template_hits = [], [], 0, {}
    num_count, char_count, uplift_endings = 0, 0, 0
    openings = set()

    for t in texts:
        t = t.strip()
        char_count += len(t)
        sents = [s for s in SENT_SPLIT.split(t) if s.strip()]
        sent_lens.extend(len(s) for s in sents)
        paras = [p for p in t.split("\n") if p.strip()]
        para_counts.append(len(paras))
        for h in HEDGES:
            hedge_hits += t.count(h)
        for name, pat in TEMPLATES:
            n = len(pat.findall(t))
            if n:
                template_hits[name] = template_hits.get(name, 0) + n
        num_count += len(NUM.findall(t))
        if paras and CLOSING_UPLIFT.search(paras[-1]):
            uplift_endings += 1
        openings.add(t[:10])

    n = len(texts)
    return {
        "样本数": n,
        "平均篇幅(字)": round(char_count / n),
        "句长中位数": round(statistics.median(sent_lens), 1) if sent_lens else 0,
        "句长标准差(节奏不对称)": round(statistics.pstdev(sent_lens), 1) if sent_lens else 0,
        "数字密度(个/千字)": round(num_count * 1000 / char_count, 2) if char_count else 0,
        "垫词率(个/千字)": round(hedge_hits * 1000 / char_count, 2) if char_count else 0,
        "升华式结尾占比": f"{uplift_endings}/{n}",
        "开头前10字唯一率": round(len(openings) / n, 2),
        "模板句式命中": template_hits or "无",
    }


def print_report(title, stats):
    print(f"\n== {title} ==")
    for k, v in stats.items():
        print(f"  {k}: {v}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="jsonl file of texts")
    ap.add_argument("--field", default="answer", help="json field holding the text")
    ap.add_argument("--ref", help="reference jsonl to compare against (field: reference)")
    args = ap.parse_args()

    print_report(args.file, analyze(load_texts(args.file, args.field)))
    if args.ref:
        print_report(f"{args.ref} (真实语料基线)", analyze(load_texts(args.ref, "reference")))
        print("\n目标：左右两栏分布接近。垫词率、模板命中、升华结尾应趋近于零；"
              "句长标准差和开头唯一率应接近基线。")


if __name__ == "__main__":
    main()
