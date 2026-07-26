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
SELF_QUOTE = re.compile(r"我说过|我早就讲过|我早就说过|我一直说|我一直讲")
NAV = re.compile(r"先看第?[一二三]|再看第?[一二三]|第[一二三]个问题|翻译一下|先说结论")
SENT_SPLIT = re.compile(r"[。！？!?…]+")
NUM = re.compile(r"\d[\d,.%]*")

# a paragraph long enough to have a body, ending in a short punchy sentence
PUNCH_PARA_MIN = 80
PUNCH_SENT_MAX = 18


def load_records(path, field):
    records = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if field not in obj:
            sys.exit(f"field '{field}' not found in record: {list(obj)}")
        records.append(obj)
    if not records:
        sys.exit(f"no records in {path}")
    return records


def analyze(texts):
    sent_lens, para_counts, hedge_hits, template_hits = [], [], 0, {}
    num_count, char_count, uplift_endings = 0, 0, 0
    self_quotes, nav_hits = 0, 0
    punch_paras, body_paras = 0, 0
    lengths = []
    openings = set()

    for t in texts:
        t = t.strip()
        char_count += len(t)
        lengths.append(len(t))
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
        self_quotes += len(SELF_QUOTE.findall(t))
        nav_hits += len(NAV.findall(t))
        for p in paras:
            if len(p) < PUNCH_PARA_MIN:
                continue
            body_paras += 1
            p_sents = [s for s in SENT_SPLIT.split(p) if s.strip()]
            if p_sents and len(p_sents[-1]) <= PUNCH_SENT_MAX:
                punch_paras += 1
        if paras and CLOSING_UPLIFT.search(paras[-1]):
            uplift_endings += 1
        openings.add(t[:10])

    n = len(texts)
    return {
        "样本数": n,
        "平均篇幅(字)": round(char_count / n),
        "篇幅中位数(字)": round(statistics.median(lengths)),
        "句长中位数": round(statistics.median(sent_lens), 1) if sent_lens else 0,
        "句长标准差(节奏不对称)": round(statistics.pstdev(sent_lens), 1) if sent_lens else 0,
        "数字密度(个/千字)": round(num_count * 1000 / char_count, 2) if char_count else 0,
        "垫词率(个/千字)": round(hedge_hits * 1000 / char_count, 2) if char_count else 0,
        "自引命中(我说过等)": self_quotes,
        "导览句命中(先看/翻译一下等)": nav_hits,
        "段末金句率(长段落)": f"{punch_paras}/{body_paras}" if body_paras else "n/a",
        "升华式结尾占比": f"{uplift_endings}/{n}",
        "开头前10字唯一率": round(len(openings) / n, 2),
        "模板句式命中": template_hits or "无",
    }


def bucket_length_match(out_records, ref_records, out_field):
    """Per-bucket length comparison for outputs whose ids match the heldout set."""
    refs = {r["id"]: r for r in ref_records if "id" in r}
    rows = {}
    for o in out_records:
        r = refs.get(o.get("id"))
        if not r or "bucket" not in r:
            continue
        b = rows.setdefault(r["bucket"], {"out": [], "ref": []})
        b["out"].append(len(o[out_field].strip()))
        b["ref"].append(len(r["reference"].strip()))
    if not rows:
        return
    print("\n== 分桶长度匹配（模型平均字数 / 真实平均字数） ==")
    for bucket, v in rows.items():
        out_avg = sum(v["out"]) / len(v["out"])
        ref_avg = sum(v["ref"]) / len(v["ref"])
        print(f"  {bucket} (n={len(v['out'])}): {round(out_avg)} / {round(ref_avg)}"
              f"  比值 {out_avg / ref_avg:.2f}")
    print("  比值应接近 1。短问题桶的比值最能暴露'不敢短'的问题。")


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

    out_records = load_records(args.file, args.field)
    print_report(args.file, analyze([r[args.field] for r in out_records]))
    if args.ref:
        ref_records = load_records(args.ref, "reference")
        print_report(f"{args.ref} (真实语料基线)", analyze([r["reference"] for r in ref_records]))
        bucket_length_match(out_records, ref_records, args.field)
        print("\n目标：两栏分布接近。垫词率、模板命中、导览句、升华结尾应趋近于零；"
              "自引、段末金句率、篇幅、句长标准差应接近基线，而不是越多越好。")


if __name__ == "__main__":
    main()
