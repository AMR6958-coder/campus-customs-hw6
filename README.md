# Campus Customs — Vendor Desk Agent

MGT 409 E1, Homework 6. An AI assistant that reads one vendor document (a quote, an invoice, a
catalog page, or a supplier email), pulls out the key facts, and recommends whether the shop
should buy, following the rules in the Campus Customs shop handbook.

- **Built with:** Python 3.14 and PydanticAI
- **Model:** `gpt-6-luna` only, through the Portkey gateway
- **Reads:** HTML, PDF and `.eml` email files
- **Never sends an email or makes a payment.** Its `send_email` and `approve_payment` tools only
  write to a log file.

Campus Customs is a made-up shop used for the course. All vendors and documents are fictional.

## Start here

- **`output/hw6_report.html`** — the results page. Double-click it; it needs no internet.
- **`output/harness.md`** — the design record: how the agent works and why.
- **`AI_prompts.md`** — every prompt given to the AI assistant during the build, by problem.

## How to run the agent

You need Python 3.14. From this folder:

**1. Install**

```
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

(On macOS or Linux use `python3.14 -m venv .venv` and `.venv/bin/python` in place of
`.venv\Scripts\python`.)

**2. Give it the gateway key**

```
copy .env.example .env
```

Open `.env` and replace the placeholder with your Portkey key. The real `.env` is git-ignored and
is not in this repository. You can also set `PORTKEY_API_KEY` in your shell and skip the file.

**3. Review one document**

```
.venv\Scripts\python agent.py --doc data/practice_docs/p01_bluehen_quote.html
```

It prints the answer as JSON: vendor, SKU, item, unit price, lead time in days, minimum order, a
decision (`recommend` or `do_not_recommend`), and a one-sentence reason. Try a PDF and an email:

```
.venv\Scripts\python agent.py --doc data/practice_docs/p05_maplemills_quote.pdf
```

```
.venv\Scripts\python agent.py --doc data/practice_docs/p08_chapelst_email.eml
```

After every run the agent appends to three logs in `output/`:

| File | What it holds |
|---|---|
| `usage_log.json` | Token counts the API reported and the dollar cost, per model call |
| `audit_trail.json` | Each tool call with its arguments and a short result, plus the final answer |
| `trap_calls.json` | Any call to `send_email` or `approve_payment`. An empty list means no document has taken over the agent |

The second look (a picture check on a would-be recommendation) uses Chrome or Edge to draw an
HTML page. Without one it skips that check for HTML and warns; PDFs are unaffected.

## Check the safety features without spending anything

```
.venv\Scripts\python safety_check.py
```

This exercises every safety feature directly and calls no model. It currently reports 56 of 57:
the one item it flags is a single failed run from development that is kept in the append-only
audit trail on purpose (see `output/harness.md`, section 17).

## What is in this repository

| Path | What it is |
|---|---|
| `agent.py`, `tools.py`, `models.py`, `prompts/` | The agent: entry point, tools and document reader, data types, instructions |
| `data/` | The course data: handbook, prices, practice and exam documents, the practice answer key, and our two red-team documents in `data/my_attacks/` |
| `output/` | Every result: the report, the harness, and the write-up and raw data for each problem |
| `count_handbook_tokens.py` | Problem 2: size and cost of the handbook |
| `cache_test.py` | Problem 4: with and without cached tokens |
| `attack_test.py` | Problem 5: the agent with no defenses |
| `defense_test.py`, `stress_test.py`, `test_second_look.py`, `safety_check.py` | Problem 6: each defense by itself, and the checks |
| `build_my_attacks.py` | Problem 7: builds our two red-team documents |
| `exam_run.py` | Problem 8: the exam documents |

Results by problem are in `output/`: `handbook_estimate.md`, `cache_test.md`, `attack_results.md`,
`defense_results.md`, `red_team.md`, `exam_results.json`, and `hw6_report.html`.

## Notes

- The test scripts call the model and cost a few cents in total. `safety_check.py` and
  `build_my_attacks.py` cost nothing.
- The logs in `output/` are a true record of every run made while building this, including the
  test runs. Entries made with the defenses switched off are marked `"defences": false`.
