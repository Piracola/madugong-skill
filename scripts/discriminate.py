#!/usr/bin/env python3
"""
Discriminator eval: can a judge model tell the skill's output from the real
Ma Qianzu answer? Imitation quality = judge accuracy approaching 50%.

Step 1 — generate judge prompts (A/B order randomized with a fixed seed):
  python scripts/discriminate.py make outputs.jsonl
  -> writes eval/pairs.jsonl  {id, prompt, answer_key}   (answer_key = which
     letter is the REAL answer; do not show the key to the judge)

Step 2 — run each prompt through any judge model, collect verdicts as jsonl
  {id, verdict}  where verdict is "A" or "B" = the one the judge thinks is real.

Step 3 — score:
  python scripts/discriminate.py score verdicts.jsonl

outputs.jsonl format: one {id, answer} per line, ids matching eval/heldout.jsonl.
"""

import json
import random
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
HELDOUT = REPO_ROOT / "eval" / "heldout.jsonl"
PAIRS = REPO_ROOT / "eval" / "pairs.jsonl"

JUDGE_TEMPLATE = """\
下面是一个知乎问题和两个回答。其中一个是马前卒（马督工）本人的真实回答，另一个是 AI 模仿他风格生成的。判断哪一个是真实回答。

【问题】{question}

【回答A】
{a}

【回答B】
{b}

只输出一个字母：A 或 B（你认为是真人回答的那个）。"""


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def make(outputs_path):
    heldout = {r["id"]: r for r in load_jsonl(HELDOUT)}
    outputs = {r["id"]: r for r in load_jsonl(outputs_path)}
    rng = random.Random(42)
    pairs, skipped = [], 0
    for qid, ref in heldout.items():
        out = outputs.get(qid)
        if not out or not out.get("answer", "").strip():
            skipped += 1
            continue
        real_is_a = rng.random() < 0.5
        a, b = (ref["reference"], out["answer"]) if real_is_a else (out["answer"], ref["reference"])
        pairs.append({
            "id": qid,
            "prompt": JUDGE_TEMPLATE.format(question=ref["question"], a=a, b=b),
            "answer_key": "A" if real_is_a else "B",
        })
    with PAIRS.open("w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"wrote {len(pairs)} judge prompts to {PAIRS}" + (f" (skipped {skipped} without outputs)" if skipped else ""))


def score(verdicts_path):
    keys = {p["id"]: p["answer_key"] for p in load_jsonl(PAIRS)}
    verdicts = load_jsonl(verdicts_path)
    correct = judged = 0
    for v in verdicts:
        key = keys.get(v["id"])
        verdict = str(v.get("verdict", "")).strip().upper()[:1]
        if key and verdict in ("A", "B"):
            judged += 1
            correct += (verdict == key)
    if not judged:
        sys.exit("no scorable verdicts")
    acc = correct / judged
    print(f"判别准确率: {correct}/{judged} = {acc:.1%}")
    print("解读: 100% = 一眼假；50% = 判别器无法区分（模仿成功）。")
    print("注意: 低于50%说明判别器把模型输出当成了真人——通常意味着它在用'哪个更长/更有数据'之类的错误特征判别，检查判别器提示词。")


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("make", "score"):
        sys.exit(__doc__)
    if sys.argv[1] == "make":
        make(sys.argv[2])
    else:
        score(sys.argv[2])


if __name__ == "__main__":
    main()
