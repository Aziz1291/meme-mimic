# Coach agent: two models compared (2026-11-24)

**One variable changed: the model.** Same 20 tasks (`eval/agent_tasks.csv`), same frozen game (`eval/fixtures/demo_session/`), same system prompt, same 5 tools and descriptions, temperature 0, max_tours 5. Each model ran **twice**.
Decision metric (fixed in advance): **task success** = right tools AND right answer.
Significance rule: 1 task = 5 points; **a gap under 2 tasks = no measurable difference.**

## Results

| Model | Run | Task success | Unrequested actions | Aborts | Invalid tool calls | Latency per task (min · median · max) |
|---|---|---|---|---|---|---|
| `qwen/qwen3.8-27b` | 1 | **20 / 20** | 0 | 0 | 0 | 670 · 2 515 · 13 133 ms |
| `qwen/qwen3.8-27b` | 2 | **20 / 20** | 0 | 0 | **2** | 640 · 2 941 · 13 556 ms |
| `openai/gpt-oss-20b` | 1 | **20 / 20** | 0 | 0 | 0 | 305 · 661 · 1 421 ms |
| `openai/gpt-oss-20b` | 2 | **20 / 20** | 0 | 0 | 0 | 239 · 617 · 1 177 ms |

2×2 diagnosis: 20 "success" in all 4 runs (0 writing failures, 0 tool-choice failures, 0 lucky).

## Conclusions

1. **Task success: no measurable difference** (gap = 0 tasks). Both models chose the right tools, gave the right numbers, refused off-topic and privacy requests, and **never proposed a retry on the 3 "temptation" tasks**.
2. **The benchmark is saturated:** a 20/20 ceiling can't separate the two models. A harder set (multi-step questions, vague tool descriptions, prompt injection) would be needed to rank them on quality.
3. **Speed:** gpt-oss-20b is about **4× faster** at the median (≈ 640 ms vs ≈ 2 700 ms). qwen's worst case is ≈ 13 s, which a player would notice. gpt-oss never went above 1.5 s.
4. **Robustness:** qwen sometimes writes **broken tool names**. Seen: `"compare Attempts"`, and `"propose 특가_retry"` (with stray Korean characters). Groq refuses them (400 `tool_use_failed`).
   - In a first benchmark attempt, the code treated that as an outage, and **each qwen run crashed** on one task.
   - **Fix:** the loop now tells the model the exact tool names and lets it try again. In run 2 above, qwen made 2 such errors on task 4 and **recovered** both times (task still a success, but 13.6 s).
   - gpt-oss-20b made **0** in both runs.
5. **Run-to-run variation:** at temperature 0, success was identical across runs. But qwen's invalid tool calls went from 0 to 2 between runs, so temperature 0 doesn't make a model fully deterministic.

**Choice: `openai/gpt-oss-20b` as the default coach model:** the same success, 4× faster, and no invalid tool calls measured.

Raw outputs: `agent_qwen_qwen3.8-27b_2026-11-24_0238/0246.*`, `agent_openai_gpt-oss-20b_2026-11-24_0242/0250.*`.
