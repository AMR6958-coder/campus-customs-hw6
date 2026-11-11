"""Problem 8: run the final defended agent on the exam documents.

The 10 documents in data/exam_docs/ have no answer key. This runs the agent
exactly as it normally is, with every defence on, on each of them, and writes
one record per document to output/exam_results.json. The agent's output is
recorded as given; nothing here edits a decision or a figure.

    .venv\\Scripts\\python exam_run.py
    .venv\\Scripts\\python exam_run.py --out output/exam_results_run2.json   # a second full run, kept separate

Each record has the fields the assignment asks for:
  File, Vendor, SKU, Unit_Price, Lead_Time_Days, Min_Order, decision, Reason,
  Trap_Tool_Called, input tokens, Cached_Tokens, Output_Tokens, Cost_USD
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import agent
from tools import now_iso

ROOT = Path(__file__).resolve().parent
EXAM_DIR = ROOT / "data" / "exam_docs"
DEFAULT_RESULT = ROOT / "output" / "exam_results.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the defended agent on the exam documents.")
    parser.add_argument("--out", default=str(DEFAULT_RESULT), help="where to write the results JSON")
    result_path = Path(parser.parse_args().out)
    if not result_path.is_absolute():
        result_path = ROOT / result_path

    records = []
    for path in sorted(EXAM_DIR.iterdir()):
        answer, usage, audit = agent.review(path.relative_to(ROOT).as_posix(), fresh=True)
        a = answer or {}
        records.append(
            {
                "File": path.name,
                "Vendor": a.get("vendor"),
                "SKU": a.get("sku"),
                "Unit_Price": a.get("unit_price"),
                "Lead_Time_Days": a.get("lead_time_days"),
                "Min_Order": a.get("min_order"),
                "decision": a.get("decision"),
                "Reason": a.get("reason") if answer is not None else f"(run failed: {audit.error})",
                "Trap_Tool_Called": audit.trap_calls > 0,
                "input tokens": usage.input_tokens,
                "Cached_Tokens": usage.cached_input_tokens,
                "Output_Tokens": usage.output_tokens,
                "Cost_USD": usage.cost_usd,
            }
        )
        trap = "  TRAP!" if audit.trap_calls else ""
        print(f"{path.name:<22} {str(a.get('decision')):<17} {str(a.get('vendor'))[:22]:<22} {a.get('sku')}  ${usage.cost_usd:.6f}{trap}")

    result_path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    recommend = sum(1 for r in records if r["decision"] == "recommend")
    traps = sum(1 for r in records if r["Trap_Tool_Called"])
    cost = sum(r["Cost_USD"] for r in records)
    print(f"\n{len(records)} documents | {recommend} recommend, {len(records) - recommend} do_not_recommend | trap calls: {traps} | ${cost:.4f}")
    print(f"Saved {result_path.relative_to(ROOT).as_posix()}  ({now_iso()})")


if __name__ == "__main__":
    main()
