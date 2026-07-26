# 评测闭环

目的：让"改了 prompt 到底更像还是更不像"变成可测量的问题，不再凭手感。

## 组成

| 文件 | 说明 |
|---|---|
| `selection.tsv` | 评测题选目（分层：短/中/长回答，议题多样，与 fewshots 严格隔离） |
| `heldout.jsonl` | 评测集本体：`{id, bucket, topic, question, reference, source}`，reference 为马前卒真实回答 |
| `pairs.jsonl` | 判别式评测的 judge prompt（由脚本生成，不要手改） |

`heldout.jsonl` 已提交到仓库，没有本地语料库也能跑评测。`selection.tsv` 改动后需在有 `docs/` 语料的机器上重跑 `python scripts/build_eval.py` 再提交。

## 评测流程

### 第 0 步：生成待测输出

用装了 skill 的模型回答 `heldout.jsonl` 里的 50 个 question，产出 `outputs.jsonl`（每行 `{"id": "q001", "answer": "..."}`，id 与评测集对应）。任何模型都行——粘贴 `publish/madugong.md` 当系统提示词，或在 Claude Code 里直接用 skill。

**注意：生成时不要让模型联网搜索这些问题的答案原文，否则测的是检索不是模仿。**

### 第 1 步：风格分布对比（无需 API，秒出）

```bash
python scripts/style_stats.py outputs.jsonl --field answer --ref eval/heldout.jsonl
```

输出两栏指标：篇幅、句长标准差（节奏不对称度）、数字密度、垫词率、模板句式命中、升华式结尾占比、开头多样性。目标是模型栏向真实语料栏收敛，其中垫词率、模板命中、升华结尾应趋近于零。

### 第 2 步：判别式评测（需要一个 judge 模型）

```bash
# 生成 A/B 判别题（真假顺序随机，种子固定可复现）
python scripts/discriminate.py make outputs.jsonl

# 把 eval/pairs.jsonl 每条的 prompt 喂给任意 judge 模型，
# 收集裁决为 verdicts.jsonl（每行 {"id": "q001", "verdict": "A"}）

# 算分
python scripts/discriminate.py score verdicts.jsonl
```

**指标解读：判别准确率越接近 50% 模仿越成功。** 100% 说明一眼假；随准确率下降，说明 judge 已无法从风格上区分真人和模型。

judge 模型建议用与生成模型**不同**的模型，避免自家风格偏好互相打掩护。

## 纪律

- `heldout.jsonl` 里的题**永远不进 fewshots.md**，反过来也一样。污染了评测集，指标就成了自欺欺人。
- 每次大改 SKILL.md / fewshots.md 后跑一轮，把两个指标记在 commit message 或 PR 描述里，形成可回溯的曲线。
