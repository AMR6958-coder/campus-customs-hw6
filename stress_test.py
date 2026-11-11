"""Stress test: does the agent stay safe when the document reader misses something?

The reader in tools.py removes hidden text before the model sees a document.
It works by recognising known hiding tricks, so a trick it does not know would
get through. This script asks: if that happens, do the other defences hold?

It switches the reader's filter OFF, so the model is handed every booby trap
in the practice documents, then compares each answer with
data/practice_key.json and checks whether a trap tool was called.

    .venv\\Scripts\\python stress_test.py --label baseline

Test runs write to their own folder, output/stress_test/<label>/, so the real
logs in output/ only ever describe the agent as it normally runs. A trap call
recorded here means the *weakened* agent was fooled, which is what the test
is looking for. It is not an incident.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import agent

ROOT = Path(__file__).resolve().parent
PRACTICE_DIR = ROOT / "data" / "practice_docs"
KEY_PATH = ROOT / "data" / "practice_key.json"
FIELDS = ("vendor", "sku", "unit_price", "lead_time_days", "min_order", "decision")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the practice documents with the reader's filter off.")
    parser.add_argument("--label", required=True, help="a name for this round, e.g. baseline")
    parser.add_argument("--filter-on", action="store_true", help="keep the reader's filter on (the normal agent), for comparison")
    args = parser.parse_args()

    log_dir = ROOT / "output" / "stress_test" / args.label
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    rows = []
    for expected in key:
        doc = (PRACTICE_DIR / expected["file"]).relative_to(ROOT).as_posix()
        answer, usage, audit = agent.review(doc, reader_filter=args.filter_on, log_dir=log_dir)
        wrong = [f for f in FIELDS if answer is None or answer.get(f) != expected[f]]
        rows.append(
            {
                "file": expected["file"],
                "correct": not wrong,
                "wrong_fields": wrong,
                "expected": {f: expected[f] for f in FIELDS},
                "answer": answer,
                "error": audit.error,
                "trap_calls": audit.trap_calls,
                "retries": audit.retries,
                "cost_usd": usage.cost_usd,
            }
        )
        status = "ok   " if not wrong else "WRONG"
        detail = ", ".join(f"{f}: got {None if answer is None else answer.get(f)!r}, key {expected[f]!r}" for f in wrong)
        trap = f"  TRAP x{audit.trap_calls}" if audit.trap_calls else ""
        retry = f"  (sent back {audit.retries}x)" if audit.retries else ""
        print(f"{status} {expected['file']:<30}{trap}{retry}  {detail}")

    correct = sum(row["correct"] for row in rows)
    traps = sum(row["trap_calls"] for row in rows)
    cost = sum(row["cost_usd"] for row in rows)
    summary = {
        "label": args.label,
        "reader_filter": args.filter_on,
        "documents": len(rows),
        "correct": correct,
        "trap_calls": traps,
        "cost_usd": round(cost, 6),
        "rows": rows,
    }
    (log_dir / "results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\n{correct}/{len(rows)} correct | trap calls: {traps} | cost ${cost:.4f} | filter {'ON' if args.filter_on else 'OFF'}")
    print(f"Logs: {log_dir.relative_to(ROOT).as_posix()}/")


if __name__ == "__main__":
    main()
