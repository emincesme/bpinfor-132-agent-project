# Week 2: a structured-output extractor, measured

Copy this into your `DECISIONS.md` and fill it in.

---

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
