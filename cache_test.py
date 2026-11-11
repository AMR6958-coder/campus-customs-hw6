"""Problem 4: what is the prompt cache worth?

Runs the agent on all 12 practice documents twice:

  uncached  the model is told not to cache the prompt at all, so every call
            pays the normal input price for the whole handbook.
  cached    the agent as it normally runs: the model caches the unchanged
            start of the prompt and reads it back at a tenth of the price.

Nothing else differs between the two rounds: same documents, same order, same
prompt, same model. Every model call from both rounds is saved to
output/cache_test.json with the token counts the API reported and the dollar
cost worked out from data/prices.json.

    .venv\\Scripts\\python cache_test.py

Three things keep the comparison honest:

* The uncached round runs first, and both rounds put the same one-line tag
  at the top of the instructions. No call has ever used that tag, so the
  cached round starts with an empty cache and we see the first call write it.
* Every call carries a header telling the gateway to call the model even if
  it has answered an identical request before. Without it the gateway replays
  the old answer with the old token counts, and nothing new is measured.
* The script checks the token counts itself (see `proof` in the output): the
  uncached round must show zero cached and zero cache-write tokens on every
  call, and the cached round must show cached tokens on every call after the
  first.

Logs for these runs go to output/cache_test/<setup>/, apart from the real logs.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import agent
from tools import now_iso

ROOT = Path(__file__).resolve().parent
PRACTICE_DIR = ROOT / "data" / "practice_docs"
KEY_PATH = ROOT / "data" / "practice_key.json"
RESULT_PATH = ROOT / "output" / "cache_test.json"
LOG_ROOT = ROOT / "output" / "cache_test"
FIELDS = ("vendor", "sku", "unit_price", "lead_time_days", "min_order", "decision")

SETUPS = [("uncached", False), ("cached", True)]  # (name, prompt_cache) in the order they run


def main() -> None:
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    prices = json.loads(agent.PRICES_PATH.read_text(encoding="utf-8"))
    tag = f"cache test {time.strftime('%Y%m%d-%H%M%S')}"
    calls: list[dict] = []
    documents: list[dict] = []

    for setup, prompt_cache in SETUPS:
        print(f"\n=== {setup} ===")
        for expected in key:
            doc = (PRACTICE_DIR / expected["file"]).relative_to(ROOT).as_posix()
            answer, usage, audit = agent.review(doc, log_dir=LOG_ROOT / setup, prompt_cache=prompt_cache, fresh=True, cache_tag=tag)
            correct = answer is not None and all(answer.get(f) == expected[f] for f in FIELDS)
            for call in usage.calls:
                calls.append({"setup": setup, "document": expected["file"], **call.model_dump()})
            documents.append(
                {
                    "setup": setup,
                    "document": expected["file"],
                    "model_calls": usage.requests,
                    "input_tokens": usage.input_tokens,
                    "cached_input_tokens": usage.cached_input_tokens,
                    "cache_write_tokens": usage.cache_write_tokens,
                    "uncached_input_tokens": usage.uncached_input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cost_usd": usage.cost_usd,
                    "cost_breakdown_usd": usage.cost_breakdown_usd,
                    "decision": answer["decision"] if answer else None,
                    "matches_key": correct,
                    "second_look": audit.second_look.status if audit.second_look else None,
                    "trap_calls": audit.trap_calls,
                    "seconds": round(audit.duration_ms / 1000, 2),
                }
            )
            print(
                f"{expected['file']:<30} calls={usage.requests} input={usage.input_tokens:>6,} cached={usage.cached_input_tokens:>6,} "
                f"write={usage.cache_write_tokens:>6,} out={usage.output_tokens:>4} ${usage.cost_usd:.6f} {audit.duration_ms / 1000:4.1f}s "
                f"{'ok' if correct else 'WRONG'}"
            )

    def rows(setup: str) -> list[dict]:
        return [c for c in calls if c["setup"] == setup]

    uncached, cached = rows("uncached"), rows("cached")
    ids = [c["response_id"] for c in calls]
    proof = {
        "uncached_every_call_has_zero_cached_tokens": all(c["cached_input_tokens"] == 0 for c in uncached),
        "uncached_every_call_has_zero_cache_write_tokens": all(c["cache_write_tokens"] == 0 for c in uncached),
        "cached_first_call_wrote_the_cache": bool(cached) and cached[0]["cached_input_tokens"] == 0 and cached[0]["cache_write_tokens"] > 0,
        "cached_every_later_call_read_the_cache": all(c["cached_input_tokens"] > 0 for c in cached[1:]),
        "no_replayed_answers_every_response_id_is_unique": len(ids) == len(set(ids)),
        "same_number_of_calls_in_both_setups": len(uncached) == len(cached),
    }
    totals = {}
    for setup, _ in SETUPS:
        docs = [d for d in documents if d["setup"] == setup]
        totals[setup] = {
            "documents": len(docs),
            "model_calls": sum(d["model_calls"] for d in docs),
            "input_tokens": sum(d["input_tokens"] for d in docs),
            "cached_input_tokens": sum(d["cached_input_tokens"] for d in docs),
            "cache_write_tokens": sum(d["cache_write_tokens"] for d in docs),
            "uncached_input_tokens": sum(d["uncached_input_tokens"] for d in docs),
            "output_tokens": sum(d["output_tokens"] for d in docs),
            "cost_usd": round(sum(d["cost_usd"] for d in docs), 8),
            "correct": sum(d["matches_key"] for d in docs),
            "trap_calls": sum(d["trap_calls"] for d in docs),
            "seconds": round(sum(d["seconds"] for d in docs), 1),
        }

    RESULT_PATH.write_text(
        json.dumps(
            {
                "run_at": now_iso(),
                "model": agent.MODEL_NAME,
                "prices_per_1m_tokens": prices[agent.MODEL_NAME],
                "cache_tag": tag,
                "proof": proof,
                "totals": totals,
                "documents": documents,
                "calls": calls,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("\nProof:")
    for name, passed in proof.items():
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
    for setup, total in totals.items():
        print(f"{setup:<9} {total['model_calls']} calls | ${total['cost_usd']:.6f} | {total['correct']}/{total['documents']} correct | traps {total['trap_calls']} | {total['seconds']}s")
    saved = 1 - totals["cached"]["cost_usd"] / totals["uncached"]["cost_usd"]
    print(f"Saved by caching: {saved:.1%}")
    print(f"Saved {RESULT_PATH.relative_to(ROOT).as_posix()} ({len(calls)} model calls)")


if __name__ == "__main__":
    main()
