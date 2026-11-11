# With and Without Cached Tokens

**Problem 4.** The handbook is the same on every call, so the model can reuse it from its cache at
a tenth of the price. This page measures what that is worth on the real agent.

Run on 2026-11-10 with `cache_test.py`. Every model call from both setups is in
`output/cache_test.json` (52 calls), with the token counts the API reported and the dollars worked
out from `data/prices.json`.

## 1. The result

| | Without cache | With cache | Saved |
|---|---|---|---|
| 12 practice documents, as run (cache starts empty) | $0.031461 | $0.005897 | **81.3%** |
| 12 practice documents, once the cache is warm | $0.031461 | $0.004575 | **85.5%** |
| Per document, warm | $0.002622 | $0.000381 | 85.5% |
| Answers matching the practice key | 12 of 12 | 12 of 12 | |
| Trap calls | 0 | 0 | |

Caching changed the price and nothing else. Both setups sent exactly the same 307,090 input tokens
and gave the same 12 answers.

## 2. The two setups

| | Without cache | With cache |
|---|---|---|
| What the model is told | `prompt_cache_options: {"mode": "explicit"}`: cache only where a breakpoint is marked. None is marked, so nothing is cached. | Nothing. Caching is the model's default. This is the agent exactly as it normally runs. |
| Documents | The 12 practice documents, in order | The same, in the same order |
| Prompt, model, tools | Identical | Identical |
| Run order | First | Second |

Three things keep the comparison fair:

- **A fresh cache.** Both rounds put the same one-line tag at the top of the instructions. No call
  had ever used that tag, so the cached round started with an empty cache and its first call can
  be seen writing it.
- **No replayed answers.** Every call carried a header telling the Portkey gateway to call the
  model even if it had answered an identical request before (see surprise 1 in section 8).
- **The agents were not changed.** The switches are options on `review()` that only
  `cache_test.py` uses.

## 3. Proof that each setup did what it was meant to

Checked by the script from the token counts the API sent back, not assumed:

| Check | Result |
|---|---|
| Without cache: every one of the 26 calls reports 0 cached tokens | Pass |
| Without cache: every one of the 26 calls reports 0 cache-write tokens | Pass |
| With cache: the first call reports 0 cached tokens and writes the cache (11,589 tokens) | Pass |
| With cache: every one of the other 25 calls reports cached tokens (10,752 to 11,592) | Pass |
| All 52 response ids are different, so no answer was a replay | Pass |
| Both setups made the same number of calls (26) | Pass |

What the totals look like:

| Token count, 12 documents | Without cache | With cache | Price per 1M |
|---|---|---|---|
| Input tokens (all) | 307,090 | 307,090 | |
| of which read from cache | 0 | 287,824 (93.7%) | $0.01 |
| of which written to cache | 0 | 13,804 (4.5%) | $0.125 |
| of which at the normal rate | 307,090 | 5,462 (1.8%) | $0.10 |
| Output tokens | 1,503 | 1,495 | $0.50 |
| Reasoning tokens | 0 | 0 | |

## 4. Cost per document

| Document | Model calls | Without cache | With cache | Saved |
|---|---|---|---|---|
| `p01_bluehen_quote.html` | 3 | $0.003636 | $0.001921 (wrote the cache) | 47.2% |
| `p02_elmcity_quote.html` | 2 | $0.002413 | $0.000333 | 86.2% |
| `p03_ivyprint_catalog.html` | 2 | $0.002415 | $0.000338 | 86.0% |
| `p04_harborstitch_quote.html` | 3 | $0.003645 | $0.000598 | 83.6% |
| `p05_maplemills_quote.pdf` | 2 | $0.002412 | $0.000347 | 85.6% |
| `p06_qtextile_quote.pdf` | 2 | $0.002418 | $0.000329 | 86.4% |
| `p07_longwharf_quote.pdf` | 2 | $0.002410 | $0.000331 | 86.3% |
| `p08_chapelst_email.eml` | 2 | $0.002431 | $0.000352 | 85.5% |
| `p09_westville_email.eml` | 2 | $0.002415 | $0.000333 | 86.2% |
| `p10_eastrock_email.eml` | 2 | $0.002434 | $0.000355 | 85.4% |
| `p11_yorkst_quote.html` | 2 | $0.002412 | $0.000332 | 86.2% |
| `p12_bluehen_quote.pdf` | 2 | $0.002419 | $0.000328 | 86.4% |
| **Total, 12 documents** | 26 | **$0.031461** | **$0.005897** | **81.3%** |
| Average per document | 2.17 | $0.002622 | $0.000491 | 81.3% |

p01 is the odd one out. It was the first call of the cached round, so it paid to write the cache:
11,589 tokens at $0.125 per 1M instead of $0.01. Every document after it read the cache. p01 and
p04 cost more than the rest in both setups because each got a third model call, the second look at
the picture.

Where the money goes:

| Cost of 12 documents | Without cache | With cache |
|---|---|---|
| Input at the normal rate | $0.030709 | $0.000546 |
| Input read from cache | $0 | $0.002878 |
| Input written to cache | $0 | $0.001726 |
| Output | $0.000751 | $0.000747 |
| **Total** | **$0.031461** | **$0.005897** |

Without the cache, input is 97.6% of the bill. With it, the output tokens, which caching cannot
touch, are 12.7% of the bill even though there are only about 125 of them per document.

## 5. The math for one ordinary document

p02, a two-call document, in each setup. The formula is the same as in Problem 2:
`cost = tokens ÷ 1,000,000 × price per 1M`.

**Without cache**

```
Call 1:  11,716 input × $0.10          = $0.00117160
             27 output × $0.50         = $0.00001350     call 1 = $0.00118510
Call 2:  11,877 input × $0.10          = $0.00118770
             81 output × $0.50         = $0.00004050     call 2 = $0.00122820
                                                         document = $0.00241330
```

**With cache**

```
Call 1:  11,567 cached × $0.01         = $0.00011567
             23 cache write × $0.125   = $0.00000288
            126 normal × $0.10         = $0.00001260
             27 output × $0.50         = $0.00001350     call 1 = $0.00014464
Call 2:  11,590 cached × $0.01         = $0.00011590
            161 cache write × $0.125   = $0.00002013
            126 normal × $0.10         = $0.00001260
             80 output × $0.50         = $0.00004000     call 2 = $0.00018862
                                                         document = $0.00033326
```

```
Saved = 1 − $0.00033326 ÷ $0.00241330 = 86.2%
```

## 6. How the real numbers compare with the Problem 2 estimate

Problem 2 priced the handbook alone, on one call: 10,058 tokens.

| | Problem 2 estimate | Measured | Why they differ |
|---|---|---|---|
| Tokens sent per call | 10,058 (handbook only) | 11,715 to 11,971 | A real call also carries the instructions (about 1,100 tokens), the tool definitions and answer form (about 400), and the document or picture. |
| Tokens read from cache per call | 10,058 | 11,567 to 11,592 on the main agent | The cache holds everything that does not change, not only the handbook: instructions and tools too. So more is cached than estimated. |
| Cost of a call, no cache | $0.0010058 | $0.00118 to $0.00125 | 17% more input, plus output. |
| Cost of a call, cache read | $0.00010058 | $0.00014 to $0.00021 | The uncached tail, small cache writes, and output are a large share of a small number. |
| Cost of the first call, cache write | $0.00125725 | $0.00147423 | 11,589 tokens written, not 10,058. |
| Calls per document | 1 (assumed) | 2, or 3 with the second look | The agent calls the model once to ask for the document and once to answer. The handbook is sent each time. |
| Cost per 1,000 calls, no cache | $1.0058 | $1.21 | |
| Cost per 1,000 calls, with cache | $0.1017 | $0.176 | |
| **Cost per 1,000 documents, no cache** | not estimated | **$2.62** | 2.17 calls per document on average. |
| **Cost per 1,000 documents, with cache** | not estimated | **$0.38** | |
| Saved by caching | 89.9% | 85.5% warm, 81.3% as run | The parts that cannot be cached do not shrink. |

The estimate was right about the handbook and right about the direction. It was about 2.6 times too
low as a cost per document, because it counted one call and the agent makes two or three. The
handbook is still most of every call: 85% of all input tokens in this test were the handbook being
sent again (26 calls × 10,058 = 261,508 of 307,090).

**One Problem 2 claim was wrong for the real agent.** It said that if every call arrived after the
cache had expired, caching would cost 25% *more* than not caching. That holds only for one call per
document. Here, the second call of a run reads what the first call just wrote, so even a document
that arrives completely cold is cheaper with caching:

```
Cold two-call document, with cache:   $0.00147423 + $0.00020187 = $0.00167610
The same document, without cache:                                 $0.00241791   (average of the ten two-call documents)
Still saved:                                                       30.7%
```

## 7. Projection: 1,000 documents a day for 30 days

30,000 documents. Assumptions, all taken from this test:

- The same mix as the practice set: 10 of every 12 documents take two model calls, 2 of 12 take
  three (a recommendation on an HTML or PDF document gets the second look).
- Documents the same size as these, and `data/prices.json` prices.
- The cache goes cold once a day (overnight) and is written again by the first document each
  morning. The model keeps a cached prompt for at least 30 minutes by default, according to the
  library's documentation; that lifetime was not measured here. At 1,000 documents spread over a
  working day, one arrives every 30 seconds or so, far inside that window.

```
Without cache:   30,000 × $0.00262171                    = $78.65

With cache:      30,000 × $0.00038121   (warm)           = $11.44
                 + 30 cold starts × $0.001323 extra      = $ 0.04
                                                           ------
                                                           $11.48

Saved:           $78.65 − $11.48 = $67.17 a month, or 85.4%
```

The cold-start figure is p01's cost in the cached round ($0.001921) minus the cost of the same
kind of document warm ($0.000598).

| Scenario, 30,000 documents | Cost | Saved against no cache |
|---|---|---|
| No cache | $78.65 | |
| Cache, cold once a day | $11.48 | 85.4% |
| Cache, cold every 30 minutes (documents arrive in separated bursts) | $13.34 | 83.0% |
| Cache, every single document arrives cold (worst case) | $51.51 | 34.5% |

Even the worst case is cheaper than switching caching off. Over a year at this volume the
difference between the first two rows is about $806.

## 8. What was surprising

1. **There are two caches, and the second one nearly spoiled the test.** The Portkey gateway keeps
   its own cache of whole answers. Send a request identical to an earlier one and it replies in
   0.1 to 0.5 seconds with the old answer, the old response id, and the *old token counts*. Its
   response header says `x-portkey-cache-status: HIT`. That is a different thing from the model's
   prompt cache, which reuses the start of a prompt and still does the work. Without the
   force-refresh header, re-running the 12 practice documents would have measured nothing and
   reported the first run's numbers again. It also means the usage log overstates cost when a
   document is repeated.
2. **Caching was already on.** Nobody asked for it. The agent built in Problem 3 was reading the
   handbook from cache from its second call. The setup that needed building was "without cache":
   the model has to be told `mode: explicit` to stop.
3. **No speed benefit.** The 12 documents took 56.3 seconds without the cache and 59.2 seconds
   with it. On prompts this size, caching is a discount, not a speed-up.
4. **One document is two or three model calls.** The handbook goes out each time, so a document
   costs more than twice what Problem 2's per-call figure suggests. The same fact makes caching
   pay inside a single run: the second call reads what the first wrote.
5. **The two agents share a cache.** The second-look agent read 10,752 tokens from cache on its
   very first call, having written nothing. Its prompt begins with the same handbook as the main
   agent's, and the cache matches on the shared beginning. Putting the handbook first paid off
   across agents, not only across documents.
6. **Every call still writes a little.** Each call writes the new end of the conversation to the
   cache (about 23 tokens on a first call, 130 to 200 on a second) at the higher write price. It is
   small, $0.0000035 to $0.000025 a call, but it never goes to zero.
7. **The picture is the expensive part of the second look.** On that call 1,219 tokens were charged
   at the normal rate, almost ten times the 126 on an ordinary call. A picture cannot be cached
   because every document's picture is different.
8. **The saving is 86%, not 90%.** Cached input is a tenth of the price, but the output tokens, the
   document itself and the picture are not cached. Once the handbook is nearly free, those are what
   is left, and the next saving would have to come from them or from making fewer calls.

## 9. Every model call

`agent` is `main` for the vendor desk agent and `second look` for the picture reader. "Normal" is
input charged at the full rate: input minus cached minus cache write. The API also reported audio
and prediction token counts, all zero; they are in `output/cache_test.json`.

| Setup | Document | Call | Agent | Input | Cached | Cache write | Normal | Output | Reasoning | Cost |
|---|---|---|---|---|---|---|---|---|---|---|
| without cache | p01 | 1 | main | 11,715 | 0 | 0 | 11,715 | 26 | 0 | $0.00118450 |
| without cache | p01 | 2 | main | 11,898 | 0 | 0 | 11,898 | 99 | 0 | $0.00123930 |
| without cache | p01 | 3 | second look | 11,971 | 0 | 0 | 11,971 | 31 | 0 | $0.00121260 |
| without cache | p02 | 1 | main | 11,716 | 0 | 0 | 11,716 | 27 | 0 | $0.00118510 |
| without cache | p02 | 2 | main | 11,877 | 0 | 0 | 11,877 | 81 | 0 | $0.00122820 |
| without cache | p03 | 1 | main | 11,716 | 0 | 0 | 11,716 | 27 | 0 | $0.00118510 |
| without cache | p03 | 2 | main | 11,873 | 0 | 0 | 11,873 | 85 | 0 | $0.00122980 |
| without cache | p04 | 1 | main | 11,718 | 0 | 0 | 11,718 | 29 | 0 | $0.00118630 |
| without cache | p04 | 2 | main | 11,896 | 0 | 0 | 11,896 | 113 | 0 | $0.00124610 |
| without cache | p04 | 3 | second look | 11,971 | 0 | 0 | 11,971 | 31 | 0 | $0.00121260 |
| without cache | p05 | 1 | main | 11,716 | 0 | 0 | 11,716 | 27 | 0 | $0.00118510 |
| without cache | p05 | 2 | main | 11,866 | 0 | 0 | 11,866 | 80 | 0 | $0.00122660 |
| without cache | p06 | 1 | main | 11,716 | 0 | 0 | 11,716 | 27 | 0 | $0.00118510 |
| without cache | p06 | 2 | main | 11,855 | 0 | 0 | 11,855 | 95 | 0 | $0.00123300 |
| without cache | p07 | 1 | main | 11,716 | 0 | 0 | 11,716 | 27 | 0 | $0.00118510 |
| without cache | p07 | 2 | main | 11,859 | 0 | 0 | 11,859 | 79 | 0 | $0.00122540 |
| without cache | p08 | 1 | main | 11,717 | 0 | 0 | 11,717 | 28 | 0 | $0.00118570 |
| without cache | p08 | 2 | main | 11,901 | 0 | 0 | 11,901 | 110 | 0 | $0.00124510 |
| without cache | p09 | 1 | main | 11,717 | 0 | 0 | 11,717 | 28 | 0 | $0.00118570 |
| without cache | p09 | 2 | main | 11,896 | 0 | 0 | 11,896 | 80 | 0 | $0.00122960 |
| without cache | p10 | 1 | main | 11,717 | 0 | 0 | 11,717 | 28 | 0 | $0.00118570 |
| without cache | p10 | 2 | main | 11,920 | 0 | 0 | 11,920 | 112 | 0 | $0.00124800 |
| without cache | p11 | 1 | main | 11,716 | 0 | 0 | 11,716 | 27 | 0 | $0.00118510 |
| without cache | p11 | 2 | main | 11,866 | 0 | 0 | 11,866 | 80 | 0 | $0.00122660 |
| without cache | p12 | 1 | main | 11,715 | 0 | 0 | 11,715 | 26 | 0 | $0.00118450 |
| without cache | p12 | 2 | main | 11,846 | 0 | 0 | 11,846 | 100 | 0 | $0.00123460 |
| with cache | p01 | 1 | main | 11,715 | 0 | 11,589 | 126 | 26 | 0 | $0.00147423 |
| with cache | p01 | 2 | main | 11,898 | 11,589 | 183 | 126 | 101 | 0 | $0.00020187 |
| with cache | p01 | 3 | second look | 11,971 | 10,752 | 0 | 1,219 | 31 | 0 | $0.00024492 |
| with cache | p02 | 1 | main | 11,716 | 11,567 | 23 | 126 | 27 | 0 | $0.00014464 |
| with cache | p02 | 2 | main | 11,877 | 11,590 | 161 | 126 | 80 | 0 | $0.00018862 |
| with cache | p03 | 1 | main | 11,716 | 11,567 | 23 | 126 | 27 | 0 | $0.00014464 |
| with cache | p03 | 2 | main | 11,873 | 11,590 | 157 | 126 | 90 | 0 | $0.00019312 |
| with cache | p04 | 1 | main | 11,718 | 11,567 | 25 | 126 | 29 | 0 | $0.00014589 |
| with cache | p04 | 2 | main | 11,896 | 11,592 | 178 | 126 | 113 | 0 | $0.00020727 |
| with cache | p04 | 3 | second look | 11,971 | 10,752 | 0 | 1,219 | 31 | 0 | $0.00024492 |
| with cache | p05 | 1 | main | 11,716 | 11,567 | 23 | 126 | 27 | 0 | $0.00014464 |
| with cache | p05 | 2 | main | 11,866 | 11,590 | 150 | 126 | 110 | 0 | $0.00020225 |
| with cache | p06 | 1 | main | 11,716 | 11,567 | 23 | 126 | 27 | 0 | $0.00014464 |
| with cache | p06 | 2 | main | 11,855 | 11,590 | 139 | 126 | 76 | 0 | $0.00018388 |
| with cache | p07 | 1 | main | 11,716 | 11,567 | 23 | 126 | 27 | 0 | $0.00014464 |
| with cache | p07 | 2 | main | 11,859 | 11,590 | 143 | 126 | 80 | 0 | $0.00018638 |
| with cache | p08 | 1 | main | 11,717 | 11,567 | 24 | 126 | 28 | 0 | $0.00014527 |
| with cache | p08 | 2 | main | 11,901 | 11,591 | 184 | 126 | 111 | 0 | $0.00020701 |
| with cache | p09 | 1 | main | 11,717 | 11,567 | 24 | 126 | 28 | 0 | $0.00014527 |
| with cache | p09 | 2 | main | 11,896 | 11,591 | 179 | 126 | 74 | 0 | $0.00018788 |
| with cache | p10 | 1 | main | 11,717 | 11,567 | 24 | 126 | 28 | 0 | $0.00014527 |
| with cache | p10 | 2 | main | 11,920 | 11,591 | 203 | 126 | 112 | 0 | $0.00020989 |
| with cache | p11 | 1 | main | 11,716 | 11,567 | 23 | 126 | 27 | 0 | $0.00014464 |
| with cache | p11 | 2 | main | 11,866 | 11,590 | 150 | 126 | 80 | 0 | $0.00018725 |
| with cache | p12 | 1 | main | 11,715 | 11,567 | 22 | 126 | 26 | 0 | $0.00014402 |
| with cache | p12 | 2 | main | 11,846 | 11,589 | 131 | 126 | 79 | 0 | $0.00018437 |
