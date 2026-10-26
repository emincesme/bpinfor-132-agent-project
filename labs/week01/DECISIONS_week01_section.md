# Week 1: the stack, the first call, and what it costs

Copy this into your `DECISIONS.md` and fill it in. Keep the headings. In
week 13 this becomes a section of your project report that you do not have
to write.

---

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

Full sweep, run live on 2026-10-26 (qwen3:4b-instruct, 6 runs per
cell), next to the course recording (12 runs per cell, Apple M4,
2026-08-10).

| cell | distinct (recording) | distinct (mine) | median latency (mine, s) |
| closed_short, t=0.0 | 1/12 | 1/6 | 0.15 |
| closed_short, t=1.0 | 1/12 | 1/6 | 0.13 |
| open_short, t=0.0 | 1/12 | 1/6 | 2.01 |
| open_short, t=1.0 | 5/12 | 5/6 | 1.40 |
| open_list, t=0.0 | 1/12 | 1/6 | 1.40 |
| open_list, t=1.0 | 11/12 | 6/6 | 1.70 |
| open_reasoning, t=0.0 | 1/12 | 1/6 | 7.56 |
| open_reasoning, t=1.0 | 12/12 | 6/6 | 7.19 |

One change to course code: `from_live` in `02_variance.py` ignored
`--full` and always ran the two live prompts. For `--full` it now takes
all four prompts from the recording, so the live run covers the same
eight cells. Nothing else changed.

Which cell still returns a single answer at temperature 1.0, and why that
one:

closed_short, t=1.0 still returned a single distinct answer. This
suggests that increasing temperature does not necessarily create
variation when the task strongly constrains the possible answer.

Which cells a test asserting exact string equality would pass on, and what
that tells me about testing this system:

It would pass on all four cells at temperature 0.0 and on closed_short
at 1.0, because each produced one distinct output. It would fail at 1.0
on open_short (5 of 6 different), open_list and open_reasoning (6 of 6
different). The more open the task, the more the wording varies, so
exact-string tests only suit tightly constrained outputs; open-ended
generation needs a different evaluation method.

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

## AI assistance

I used ChatGPT to help explain concepts, understand the starter code and TODOs,
and assist with debugging and drafting code. I reviewed and understood the code
and text before including them in the project.
