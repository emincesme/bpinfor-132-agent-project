# Decisions

## Week 1

**Run conditions.** Everything below was produced on:

- machine: MacBook Air, Apple M2, 8 GB RAM
- model: qwen3:4b-instruct
- served Ollama, one request at a time, locally
- date: 2026-10-03

Every number in this file is meaningless without those four lines, so they
are stated once here and referred to rather than repeated.

### 1. Machine and model set

I am running the required model set.

[If you could not run the optional models, say so and say what you will do
before week 9. This is a constraint on your project, not a failure, and
naming it now is worth more than discovering it in week 9.]

### 2. The first call

| | |
| finish reason | stop |
| prompt tokens | 24 |
| completion tokens | 45 |
| elapsed | 16.66 s |

One sentence on the finish reason: what my program would do differently if
it came back as a truncation rather than a normal stop.

If the response was truncated instead of ending normally, I would not treat it as a complete successful answer and would retry with a larger output limit or otherwise handle it as incomplete.

### 3. Variance

| cell | distinct (recording) | distinct (mine) | median latency |
| closed_short, t=0.0 | 1/12 | 1/6 | 0.12 |
| closed_short, t=1.0 | 1/12 | 1/6 | 0.11 |
| open_list, t=0.0 | 1/12 | 1/6 | 1.28 |
| open_list, t=1.0 | 11/12 | 6/6 | 1.28 |

Which cell still returns a single answer at temperature 1.0, and why that
one:

[closed_short, t=1.0 still returned a single distinct answer. This suggests that increasing temperature does not necessarily create variation when the task strongly constrains the possible answer.]

Which cells a test asserting exact string equality would pass on, and what
that tells me about testing this system:

[An exact-string equality test would be stable for closed_short at both temperatures and for open_list at temperature 0.0, because each produced only one distinct output. It would be unreliable for open_list at temperature 1.0, where all six runs produced different strings. This shows that exact-string tests are only appropriate when the output is sufficiently constrained; for open-ended generation, a different evaluation method is needed.]

**The sentence that carries into week 10.** In my runs, repeated outputs were reliable for tightly constrained tasks and at temperature 0.0, but not for open-ended generation at temperature 1.0, where the exact wording changed between runs.

### 4. The cold start

- cold call: 3.33 s
- warm call: 0.12 s
- ratio: 27.8x

What this implies for a system that uses more than one model, and what I
will do about it:

The cold call was about 27.8 times slower than the warm call, so switching
between models inside one request could add significant loading latency if
a model has to be loaded into memory. I would therefore avoid unnecessary
model switching inside a request and route to the appropriate model early.

### 5. Cost, estimated

A 200-case golden set, at the token cost of my long case:

| | one run | nightly for the semester |
| small tier | 0.03 EUR | 3.28 EUR |
| large tier | 2.49 EUR | 244.14 EUR |

Estimates against the price list dated [date in `project/prices.py`], not
measurements. Running locally, my actual monetary cost was zero.

Which tier I would run nightly, which I would run before a release, and why
not the same one for both:

I would use the small tier for nightly evaluation because it is much cheaper
to run repeatedly. I would use the large tier before a release, where the
higher cost is easier to justify because the evaluation is run less often.
Using the large tier every night would make the repeated evaluation much
more expensive.

### Deferred

Nothing deferred this week.

## Week 2

**Run conditions.** model: qwen3:4b-instruct | temperature: 0.0 | prompt version: week02-zero-shot-v1 |
served locally | date: 2026-10-05 | scored on: my own machine

### 1. The output contract

The conventions I chose, and why:

- due_date, when the message states no date: null, so the model does not
  invent one.
- due_date, when the message states only a relative expression ("tomorrow",
  "end of the month"): null, because the model does not know today's date and
  a relative expression has no fixed calendar date. Dates are YYYY-MM-DD, and
  DD/MM/YYYY is read day first, because the corpus is European.
- quote, and what "verbatim" means in my scorer: an exact `in` check against
  the message. No lowercasing, no stripping punctuation.
- what my scorer does with a record that failed validation: it counts it as
  wrong on every field and increments `invalid`; it never skips it.

A scorer that skips unparseable records reports a number that improves as the
model gets worse.

### 2. Zero-shot, per field

| field | correct | of |
| category | 8 | 10 |
| urgency | 9 | 10 |
| due_date | 6 | 10 |
| quote | 10 | 10 |
| invalid records | 0 | 10 |

My prediction, written before block 3: examples will help overall, with no
single field in mind, because they highlight where the model should focus.

### 3. Few-shot

Examples chosen, and the job each one does:

| example | why it is in the block | field it should move |
| EX-01 (en, badge reader) | boundary between access and facilities | category |
| EX-03 (de, laptop) | shows DD/MM/YYYY converted to YYYY-MM-DD, in German | due_date |
| EX-04 (en, intranet notice) | shows a relative expression ("next week") giving null | due_date |

| field | zero-shot | few-shot | move |
| category | 8 | 6 | −2 |
| urgency | 9 | 9 | 0 |
| due_date | 6 | 8 | +2 |
| quote | 10 | 10 | 0 |

### 4. What got worse

`category` got worse: 8/10 to 6/10 (−2). REQ-10 was fixed, but REQ-01,
REQ-04 and REQ-09 became wrong, and REQ-08 stayed wrong.

My hypothesis for REQ-04: example EX-01 (badge reader at the side entrance,
labelled access) shares the words "entrance" and "door" with it, so the model
may have copied the label from surface similarity. I did not test this, and
I cannot explain REQ-01 and REQ-09. With ten records, some of it may be noise.

`due_date` improved (6/10 to 8/10), but REQ-01 ("tomorrow") and REQ-10 ("end
of the month") still get an invented date, only a different one.

### 5. What the examples cost

- extra input tokens per call: 223 (measured, local qwen3:4b-instruct tokenizer)
- per thousand calls: 223,000
- estimated euros per thousand calls on the small tier: 0.04 EUR
  (223,000 × 0.20 / 1,000,000), against the price list dated 2026-08-10.
  Estimate, not a measurement.

Run locally, so the monetary cost was zero.

### 6. Ship it or not

I would ship the few-shot variant. The total is the same (33/40 in both), so
the decision rests on how costly each error is: an invented due date is
worse than a wrong category, because a wrong category is easy for a human to
spot and reroute, while a wrong date can pass unnoticed. Few-shot cut due_date
errors from four to two, at the price of three new category errors.

This is weak evidence: one run, ten records, a 4B model, and two invented
dates (REQ-01, REQ-10) remain.

What would change my mind: if on a larger sample (20 to 30 messages) the
category loss persisted, I would go back to zero-shot. I would also test a
smaller example block (EX-03 and EX-04 only, dropping EX-01); if it keeps the
due_date gain without the category loss, I would ship that one instead.

### Sensitivity variant

Variant assigned: none was assigned; I chose `role`. What I changed: I
prepended "You are a senior service desk analyst." to the few-shot prompt,
nothing else. What moved: category 6/10 to 7/10 (+1), urgency 9/10 to 10/10
(+1); due_date (8/10) and quote (10/10) did not move. Total tokens went from
5018 to 5084 over ten documents.

My prediction, written before running: the role would improve category and
urgency and leave due_date and quote unchanged. The result matched.

Limits: one run, ten records, and each +1 is a single message. I did not
inspect which messages changed, so I cannot say whether errors disappeared or
changed shape. The per-language counts (5, 3, 2 documents) are too small to
say anything about a language. A one-line change moved two fields, which is
the point of this block.

### The gold set

Ten cases written to `artifacts/goldset.json`, tagged by language.

One thing my scorer cannot currently detect:

One thing my scorer cannot currently detect: whether a quote actually
supports the urgency decision. It only checks that the quote appears in the
message, so a verbatim but useless quote (for example just "The") would
score as correct.

### Deferred

- Test of a smaller example block (EX-03 and EX-04 only, without EX-01) to
  check whether EX-01 caused the category regressions. Not run: time.
- Optional extras from the lab brief: the comparison on qwen2.5:7b, a one-
  sentence fix for the invented due dates, and an eleventh adversarial
  document. Not attempted: time.
- Per-message inspection of the role variant. The sensitivity script prints
  counts only, so I do not know which messages changed.

## Week 3

**Run conditions.** classifier model: qwen3:4b-instruct | answering model: qwen3:4b-instruct |
temperature: 0.0 | served locally | date: 2026-10-06 | scored on: my own machine

### 1. The five route definitions

| route | definition, one sentence, in terms of what the help desk must do |
| request | The help desk opens a new record for something broken, missing, or needed, and starts the work to fix or provide it. |
| info | The help desk answers a question about a service, procedure, opening time, or form, without opening a record or starting any work. |
| status | The help desk finds a record that already exists and tells the sender where it stands, without opening a new one. |
| complaint | The help desk acknowledges the sender's dissatisfaction with how the service handled something and escalates it. |
| other | The help desk does no work of its own: it points the sender to another department, declines advice it cannot give, or ignores spam and instructions aimed at the system. |

My convention for the four ambiguous queries:

I adopt the convention in `AMBIGUITY_NOTE`, written down before the full
run. A message that reports an unresolved problem and complains about its
handling is `complaint` (Q-16, Q-18); a follow-up without dissatisfaction
is `status` (Q-13); a fault report that also asks a procedural question is
`request` (Q-24).

Do my definitions match the ones in `queries.py`? Yes in substance. Mine
are phrased as help desk actions, but they draw the same boundaries, so
the accuracy number measures the classifier rather than a difference in
convention.

### 2. The policy layer

Before choosing a threshold, the confidence values I saw were: min 0.0,
max 0.999, 5 distinct values across 24 queries.

- confidence floor: 0.5, because 21 of 24 values were 0.99 or above,
  including both misroutes (Q-20, Q-21), so no threshold separates right
  from wrong; 0.5 fires only on Q-22 (0.0, a correct route), one harmless
  reroute that keeps a safety net for genuine uncertainty.
- evidence check: the query goes to the safe default, because the
  evidence is what a human reviewing a misroute reads, and a fabricated
  span makes the decision unauditable.
- safe default: `info`, because that specialist takes no action on the
  sender's behalf, so a misroute into it costs one unhelpful reply and
  nothing has to be undone.

How often each check fired: below_threshold 1, evidence_not_verbatim 0,
invalid_decision 0.

The evidence and invalid checks never fired: every span came back
verbatim (24/24) and no decision was invalid. The threshold fired once,
on a correct route, which together with the distribution above shows a
useless signal rather than a very good classifier. That query, Q-22, is a
prompt injection; it was rerouted from `other` to `info`, whose
instruction does not forbid following instructions in the message, so
for it the safe default was not the safest place.

### 3. Route accuracy

| route | correct | of |
| request | 7 | 7 |
| info | 5 | 5 |
| status | 4 | 4 |
| complaint | 4 | 4 |
| other | 1 | 4 |

Overall 21/24. Excluding the four ambiguous: 17/20. Scored against
`applied_route`, because that is what the sender received; scoring
`decision.route` would take credit for decisions the policy overrode.

Confusion pairs, with direction:

| gold | applied | count |
| other | info | 3 |

The route carrying most of the error is `other`. The fix is a definition,
because all three misroutes point into `info` and none in the reverse
direction: `info` is defined by the message being a question, so
out-of-scope questions (legal advice in Q-20, another department in Q-21)
fall into it.

### 4. What routing cost

- monolith: 8,322 tokens over 24 queries
- router: 12,915 tokens over 24 queries
- the classifying call alone: 8,215 tokens, which is 64 per cent of the
  routed total

I predicted that share would be: no prediction recorded before measuring.

The share is high because the classifier's prompt carries every route
definition and the JSON schema on every call, while each specialist
carries only its own short instruction. The router costs 55 per cent more
tokens than the monolith and took 318.1 s against 64.1 s on this machine.

### 5. What routing bought

One thing a specialist can be forbidden to do that the monolith cannot be
given:

The `status` specialist must never state or guess a status or a date. In
the monolith that rule would also apply to `request` messages, whose job
includes extracting a due date, so it can only be written as "if this is
a follow-up", which depends on the monolith classifying correctly in its
head. In the router the rule is unconditional, because only status
messages reach that specialist.

Would I ship the router: not yet. Evidence: 21/24 routed correctly, but
the monolith's replies were not scored, so the only measured difference
is cost (55 per cent more tokens, about five times slower). What would
change my mind: fixing the `info` definition so that `other -> info`
disappears, and scoring both systems' replies for rule violations (an
invented time, a guessed status, a followed injection); if the monolith
breaks rules the specialists do not, the guarantees justify the cost.

### 6. Stretch variant

Variant assigned: voting, k=3, temperature 0.7 (none assigned, chosen by
me). Result: zero split votes across 24 queries, including the four
ambiguous ones; accuracy unchanged at 21/24 with the same `other -> info`
pairs.

Nothing ever disagreed, and that is the result. It cost 24,648 tokens and
312.5 s, three times the single classifying call, and bought nothing: the
errors are systematic, caused by the `info` definition, so sampling the
same model again cannot fix them. As a detector of uncertain messages,
voting finds nothing on this model, the same as the confidence score.

### The gold set

`artifacts/goldset.json` now holds 34 cases: 10 from week 2 and 24 added
today (source: own), with the four ambiguous ones tagged.

### Deferred

- Homework, done after the session: the week 2 extractor is wired behind
  the `request` route. `extract()` and `SYSTEM_ZERO_SHOT` are imported from
  `labs/week02/starter/extractor.py`; the three shipped examples (EX-01,
  EX-03, EX-04) are copied into `routes.py`, because `02_few_shot.py`
  imports a `scoring` module that collides with week 3's. Rerun on
  2026-10-06, qwen3:4b-instruct: routing unchanged at 21/24; router 14,538
  tokens (+1,623, about 232 per request query, matching week 2's
  example-block cost); the routing call is now 57 per cent of the routed
  total. Sections 2 to 6 report the in-session run.
- Model routing (variant A) was not run: a second, larger model does not
  fit alongside the first on an 8 GB machine.
- The route definition I would rewrite first is `info`, limited to
  questions about the help desk's own services; I expect `other -> info`
  to drop.

## AI assistance

**Week 1:** I used ChatGPT to help explain concepts, understand the starter
code and TODOs, and assist with debugging and drafting code. I reviewed and
understood the code and text before including them in the project.

**Week 2:** I used Claude to explain the task and the code step by step, help
with debugging, review my answers, and draft some text and code, including the
system prompt wording, the gold-set `expected_behavior` sentences, parts of the
scorer and of the sensitivity variant, and drafts of the DECISIONS entries. I
read, adjusted, and ran these myself, and I can explain them in my own words.

**Week 3:** I used Claude to explain the task, the starter code and the
policy-layer concepts step by step, and to draft code and text, including
`classify`, `apply_policy`, `score_routes`, the gold-set update, the voting
variant, the extractor wiring behind the `request` route, the `status`, `other`
and monolith prompt wording, the English wording of my route definitions, and 
drafts of the DECISIONS entries. The decisions are mine: the route definitions, 
the confidence threshold after reading the distribution, the safe default, 
adopting the ambiguity convention, the diagnosis of the `info` definition, and
the stretch variant. I read, adjusted, and ran everything myself.

All numbers in this report come from my own runs.