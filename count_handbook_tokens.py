"""How many tokens is the shop handbook, and what does it cost to send?

Problem 2. The vendor desk agent sends data/shop_handbook.md to the model on
every call, so the handbook is a fixed cost we pay each time. This script
measures it two ways and prices it with data/prices.json.

1. Offline estimate: tiktoken's o200k_base encoding, the tokenizer OpenAI's
   recent models use. Free, instant, no network.
2. Measured (--measure): ask gpt-6-luna itself through the Portkey gateway.
   We send one tiny request without the handbook and one with it. The API
   reports how many input tokens it counted for each; the difference is the
   handbook as the model really counts it. The handbook is then sent three
   more times with a different question each time, to see how many of its
   tokens the API reports as read from cache.

Run from the Homework 6 folder:

    .venv\\Scripts\\python count_handbook_tokens.py            # offline only
    .venv\\Scripts\\python count_handbook_tokens.py --measure  # plus 5 small API calls

Results are printed and saved to output/handbook_tokens.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import tiktoken
import truststore

# Verify HTTPS with the Windows certificate store instead of Python's bundled
# list. This machine's network presents a certificate only Windows knows, and
# without this line both the tokenizer download and the gateway call fail.
truststore.inject_into_ssl()

ROOT = Path(__file__).resolve().parent
HANDBOOK_PATH = ROOT / "data" / "shop_handbook.md"
PRICES_PATH = ROOT / "data" / "prices.json"
RESULT_PATH = ROOT / "output" / "handbook_tokens.json"

MODEL = "gpt-6-luna"  # the only model this homework may call
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").strip()

# A stand-in system message for the "without the handbook" request.
PLACEHOLDER = "Hello"
QUESTION = "Reply with the single word OK."


def offline_count(text: str) -> tuple[int, str]:
    """Count tokens locally. Returns (count, name of the encoding used)."""
    try:
        encoding = tiktoken.encoding_for_model(MODEL)
    except KeyError:
        # tiktoken has no entry for gpt-6-luna, so use the current OpenAI encoding.
        encoding = tiktoken.get_encoding("o200k_base")
    return len(encoding.encode(text)), encoding.name


def measured_count(handbook: str) -> dict:
    """Ask the model, through the gateway, how many input tokens it sees."""
    from openai import OpenAI

    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("PORTKEY_API_KEY is not set, so --measure cannot run.")
    client = OpenAI(base_url=PORTKEY_BASE_URL, api_key=api_key, timeout=90, max_retries=2)

    def ask(system_text: str, question: str = QUESTION) -> dict:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": question},
            ],
            max_completion_tokens=16,
            reasoning_effort="none",
        )
        usage = response.usage
        details = usage.prompt_tokens_details.model_dump() if usage.prompt_tokens_details else {}
        return {
            "model_reported": response.model,
            "input_tokens": usage.prompt_tokens,
            "cached_input_tokens": details.get("cached_tokens") or 0,
            "cache_write_tokens": details.get("cache_write_tokens") or 0,
            "output_tokens": usage.completion_tokens,
        }

    without = ask(PLACEHOLDER)
    with_handbook = ask(handbook)
    # The handbook again, each time followed by a different question. This is
    # what the agent will do (same handbook, a different vendor document), and
    # it is the case the model's prompt cache is built for: the unchanged start
    # of the prompt is read from cache. The question must differ, because a
    # request identical to an earlier one tells us nothing new about caching.
    stamp = time.strftime("%H%M%S")
    repeats = []
    for number in ("one", "two", "three"):
        time.sleep(2)
        repeats.append(ask(handbook, f"Reply with the single word OK. (check {number}, {stamp})"))

    placeholder_tokens, _ = offline_count(PLACEHOLDER)
    return {
        "without_handbook": without,
        "with_handbook": with_handbook,
        "repeat_calls": repeats,
        "placeholder_tokens": placeholder_tokens,
        # Everything else in the two requests is identical, so the difference
        # is the handbook minus the placeholder it replaced.
        "handbook_tokens": with_handbook["input_tokens"] - without["input_tokens"] + placeholder_tokens,
    }


def cost(tokens: int, price_per_1m: float) -> float:
    """Dollars for `tokens` tokens at `price_per_1m` dollars per million."""
    return tokens / 1_000_000 * price_per_1m


def main() -> None:
    handbook = HANDBOOK_PATH.read_text(encoding="utf-8")
    prices = json.loads(PRICES_PATH.read_text(encoding="utf-8"))[MODEL]

    estimate, encoding_name = offline_count(handbook)
    result: dict = {
        "handbook_file": str(HANDBOOK_PATH.relative_to(ROOT)).replace("\\", "/"),
        "characters": len(handbook),
        "bytes": len(handbook.encode("utf-8")),
        "words": len(handbook.split()),
        "offline": {"encoding": encoding_name, "tokens": estimate},
        "prices_per_1m": prices,
    }
    print(f"Handbook: {result['characters']:,} characters, {result['words']:,} words")
    print(f"Offline estimate ({encoding_name}): {estimate:,} tokens")

    tokens = estimate
    if "--measure" in sys.argv[1:]:
        measured = measured_count(handbook)
        result["measured"] = measured
        tokens = measured["handbook_tokens"]
        print(f"Without handbook: {measured['without_handbook']}")
        print(f"With handbook:    {measured['with_handbook']}")
        for i, repeat in enumerate(measured["repeat_calls"], start=1):
            print(f"Handbook again {i}: {repeat}")
        print(f"Measured by {MODEL}: {tokens:,} tokens")

    plain = cost(tokens, prices["input_per_1m"])
    cached = cost(tokens, prices["cached_input_per_1m"])
    write = cost(tokens, prices["cache_write_per_1m"])
    result["tokens_used_for_cost"] = tokens
    result["cost"] = {
        "one_call_no_cache": plain,
        "thousand_calls_no_cache": 1000 * plain,
        "one_call_cache_write": write,
        "one_call_cache_read": cached,
        "thousand_calls_with_cache": write + 999 * cached,
    }
    print(f"\nCost of the handbook alone, using {tokens:,} tokens:")
    for name, value in result["cost"].items():
        print(f"  {name:<28} ${value:.6f}")

    RESULT_PATH.parent.mkdir(exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved {RESULT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
