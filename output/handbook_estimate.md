# Size Up the Handbook

**Problem 2.** The vendor desk agent sends `data/shop_handbook.md` to the model on every call, so
the handbook is a fixed cost paid each time. This page records how big it is in tokens and what
that costs, with and without cached tokens.

Measured on 2026-11-10 with `count_handbook_tokens.py`. Raw numbers are in
`output/handbook_tokens.json`.

## 1. The token count

**The handbook is 10,058 tokens.**

| Measure | Value |
|---|---|
| File size | 29,241 bytes, 338 lines |
| Text as Python reads it | 28,903 characters, 6,127 words |
| Tokens | **10,058** |

That works out to about 2.9 characters per token, lower than the usual 4 for plain English. The
handbook is mostly tables of SKU codes and prices, which break into many small tokens.

### How the count was obtained

It was counted two independent ways, and they agree exactly.

**Way 1: offline, with OpenAI's tokenizer.** The `tiktoken` library was given the handbook text and
the `o200k_base` encoding (the one OpenAI's current models use; `tiktoken` has no entry for
`gpt-6-luna` by name). Result: **10,058 tokens**. No network call, no cost.

**Way 2: asking `gpt-6-luna` itself, through Portkey.** Two requests were sent that were identical
except for the system message, and the API reported how many input tokens it counted for each:

| Request | System message | Input tokens reported |
|---|---|---|
| A | the word "Hello" (1 token) | 18 |
| B | the whole handbook | 10,075 |

```
handbook tokens = B − A + the placeholder that the handbook replaced
                = 10,075 − 18 + 1
                = 10,058
```

The model's own count matches the offline count, so 10,058 is the number used below.

One detail: the file is stored with Windows line endings. Python converts those to plain line
breaks when it reads a text file, and that is the text the agent will send. Counted with the
Windows line endings left in, the handbook would be 10,069 tokens, 11 more.

## 2. The prices

From `data/prices.json`, for `gpt-6-luna`, in dollars per 1,000,000 tokens:

| Kind of token | Price per 1M | Meaning |
|---|---|---|
| Input | $0.10 | Text sent to the model at the normal rate |
| Cached input | $0.01 | Text the model has seen recently and reads from its cache |
| Cache write | $0.125 | Text being stored in the cache for the first time |
| Output | $0.50 | Text the model writes back (not part of the handbook's cost) |

The formula for everything below:

```
cost = tokens ÷ 1,000,000 × price per 1M
```

## 3. Without cached tokens

Every call pays the normal input rate for the whole handbook.

```
One call:      10,058 ÷ 1,000,000 × $0.10 = $0.0010058     (about a tenth of a cent)
1,000 calls:   $0.0010058 × 1,000         = $1.0058        (about $1.01)
```

## 4. With cached tokens

Caching splits calls into two kinds. The first call stores the handbook and pays the cache-write
rate, which is higher than the normal rate. Every call after that reads it back at the cached rate,
which is one tenth of the normal rate.

```
A call that reads the cache:   10,058 ÷ 1,000,000 × $0.01  = $0.00010058   (about a hundredth of a cent)
The call that writes it:       10,058 ÷ 1,000,000 × $0.125 = $0.00125725
```

For 1,000 calls made close together, that is 1 write followed by 999 reads:

```
1 write:       1 × $0.00125725   = $0.00125725
999 reads:   999 × $0.00010058   = $0.10047942
                                   -----------
1,000 calls:                       $0.10173667     (about $0.10)
```

If the write is ignored and all 1,000 calls are priced at the cached rate, the figure is
`1,000 × $0.00010058 = $0.10058`. The two differ by about a tenth of a cent.

## 5. Side by side

| Handbook alone | One call | 1,000 calls |
|---|---|---|
| Without cached tokens | $0.0010058 | **$1.0058** |
| With cached tokens | $0.00010058 (a cache read) | **$0.1017** (1 write + 999 reads) |
| | $0.00125725 (the first call, a cache write) | |

```
Saving on 1,000 calls = $1.0058 − $0.1017 = $0.9041
As a share            = $0.9041 ÷ $1.0058 = 89.9%
```

Caching cuts the handbook's cost by about 90%. It pays for itself on the second call:

```
2 calls without cache:  2 × $0.0010058            = $0.0020116
2 calls with cache:     $0.00125725 + $0.00010058 = $0.00135783
```

## 6. Does the cache actually work? (checked, not assumed)

The handbook was sent three more times through Portkey, each time followed by a different question.
This is what the agent will do: same handbook, a different vendor document each time.

| Call | Input tokens | Read from cache | Written to cache | Normal rate |
|---|---|---|---|---|
| Handbook, first time | 10,075 | 0 | 10,072 | 3 |
| Handbook again, new question | 10,083 | 10,061 | 19 | 3 |
| Handbook again, new question | 10,083 | 10,061 | 19 | 3 |
| Handbook again, new question | 10,083 | 10,061 | 19 | 3 |

On every later call the model read 10,061 tokens from cache. That covers the whole handbook
(10,058) plus 3 tokens of message framing, so the estimate in section 4 matches what the API bills.

## 7. What this means for the agent, and what the estimate does not cover

- **The handbook goes first in the prompt and never changes.** The cache matches the start of the
  prompt. Anything that varies (the vendor document) must come after it, and the handbook text must
  be identical on every call.
- **The cache has to stay warm.** The 1,000-call figure assumes the calls come close enough
  together that the cached copy is still there. How long `gpt-6-luna` keeps it was not measured. If
  every call arrived after the cache had expired, each would pay the write rate:
  `1,000 × $0.00125725 = $1.257`, which is 25% more than not caching at all.
- **This is the handbook alone.** A real call also pays for the instructions, the vendor document,
  and the model's answer at $0.50 per 1M output tokens. Those are added when the agent is built.
- **Checked later against the real agent.** Problem 4 (`output/cache_test.md`) measured both
  setups on the 12 practice documents. The estimate held for the handbook, but a real document is
  two or three model calls, so it costs about 2.6 times the per-call figure here, and the saving
  is 85.5% rather than 89.9%. The warning above about a cold cache costing 25% more applies to one
  call per document; the real agent's second call reads what its first wrote, so it stays cheaper.
- **Cost of producing this estimate:** 15 small calls carrying the handbook, about 151,000 input
  tokens in total, under 2 cents even if none had been cached.
