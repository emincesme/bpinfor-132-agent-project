# Week 10, the evaluation harness

Copy this into your project `DECISIONS.md` and fill it in. In week 13 this
becomes a section of your report you do not have to write.

This is the first week whose numbers are ABOUT your other weeks, so every
figure needs to say which runs it covers and when they were recorded.

## Conditions

- Traces covered: how many, from which weeks, recorded when:
  379 traces in `artifacts/traces.jsonl`: 246 lab traces from weeks 1 to 9,
  2026-10-03 to 2026-11-10 (week 9 = the 5 course replay traces), and 133
  app traces, 116 from `python -m app.run --batch --repeat 2` on 2026-11-24
  (41 min) plus 17 ad-hoc runs from 2026-11-02 to 2026-11-10.
- Judge model and version: qwen3:4b-instruct (Ollama id 0edcdef34593),
  local Ollama 0.40.17, temperature 0, through DeepEval's OllamaModel.
- Judge threshold: 0.5.
- Harness versions (deepeval, ragas, pytest): deepeval 4.3.4, pytest 9.1.1.
  ragas not installed: it would downgrade openai 3.29.0 to 1.109.1, which
  our pydantic-ai needs.
- Run date: 2026-11-24.

## The free layer

| week | runs | accuracy | consistency | robustness | predictability | safety |
| 5 | 20 | 0.10 | 0.67 | n/a | 0.00 | 0.00 |
| 8 | 16 | 0.19 | n/a | n/a | 0.77 | 0.54 |
| 9 | 5 | 1.00 | n/a | n/a | n/a | n/a |
| app | 133 | 0.68 | 0.97 | n/a | 0.00 | 1.00 |

`01_free.py`, 2026-11-24, 0.31 s, no model calls. Accuracy counts runs that
ended ok, not correct answers. The app's predictability 0.00 and safety 1.00
are the same 42 approval-gate stops: the reason sits in the step detail,
which predictability does not read.

Which week has the best accuracy, and what do its other columns say:
Week 9, 1.00 over 5 clean replay runs; the other four are n/a because
nothing was repeated, perturbed or failed.

Which week has the best predictability, and what does its accuracy say:
Week 8, 0.77 (10 of 13 failures flagged); its accuracy is 0.19 because the
faults were injected on purpose.

In one sentence: what ranking these systems by accuracy alone would have
told you, and why it would have been wrong:
Accuracy ranks week 9 first, but it is the week we know least about, while
week 8, ranked low, is the one whose failures we can see.

### The n/a cells

List every dimension that returned None, and for each one say whether it is
an ABSENCE (you have no evidence yet) or a DEFECT (you could have had
evidence and your instrumentation threw it away).

| week | dimension | absence or defect | what would fix it |
| 5 | robustness | defect: architecture in the case id | case id = the task, architecture in settings |
| 8 | robustness | defect: policy in the case id | case id = the fault, policy in settings |
| 8 | consistency | absence: each case ran once | run each case twice |
| 9 | consistency, robustness | absence: only 5 clean replay traces; `02_break.py` wrote json, not traces | record the sweep as traces |
| 9 | predictability, safety | absence: no run failed | the perturbed runs would supply failures |
| app | robustness | absence: one condition only | rerun the batch under a fault or a paraphrase |

The case ids in weeks 5 and 8 encode something they should not. Say what,
and what it cost you:
Week 5 put the architecture and run number into the case id
(`A-baseline-run1`), week 8 the policy (`flaky-baseline`), so repeats and
conditions look like separate cases. This cost week 5 its run-to-run
consistency and both weeks their robustness.

## The labels

The label you disagreed with, and your reasoning:
L-07, the honest "I do not have information", labelled fail. It invents
nothing, so fail feels wrong, but it does not answer, so pass is wrong too:
a binary label cannot say "honest refusal".

Whether you changed the label or kept it, and why:
Kept fail: the criterion asks whether the question was answered, and
honest refusals are rewarded by safety instead. The judge agreed (0.30).

## The judge

Agreement with the hand labels at your chosen threshold:
12 of 12 (1.00) at 0.5, live 2026-11-24. The course's own recording gives
the same score on 11 of 12 cases (L-07: 0.2 there, 0.3 here, fail both).

| | human pass | human fail |
| judge pass | 5 | 0 |
| judge fail | 0 | 7 |

The threshold sweep:

| threshold | agreement | false pass | false fail |
| 0.15 | 0.50 | 6 | 0 |
| 0.25 | 0.58 | 5 | 0 |
| 0.35 | 0.75 | 3 | 0 |
| 0.45 | 1.00 | 0 | 0 |
| 0.50 | 1.00 | 0 | 0 |
| 0.55 | 1.00 | 0 | 0 |
| 0.65 | 0.92 | 0 | 1 |
| 0.75 | 0.83 | 0 | 2 |
| 0.85 | 0.83 | 0 | 2 |

The band where agreement is perfect:
0.45 to 0.55 on the grid: the highest fail is 0.4 (L-06, L-11, L-12, one
invented detail each), the lowest pass 0.6 (L-05).

Where your threshold sits inside that band, and who chose it:
0.5, in the middle. Nobody chose it: it is the DeepEval default, kept by
the starter. 0.45 sits on a cliff, since at 0.40 the three invented
answers pass.

Which of false pass and false fail is worse for YOUR system, in one sentence
that names the consequence rather than the metric:
A false pass, because a resident would get an invented fee, deadline or
office with a green gate behind it.

## Cost

| layer | model calls | wall clock | can it run on every commit |
| deterministic checks | 0 | 0.09 s, 6 free gates (2.9 s with pytest start-up) | yes |
| the four dimensions | 0 | 0.31 s, 379 traces | yes |
| the judge | 12 cases plus GEval's step generation | 2 min 5 s, 9.9 s per case (first 40 s, model load) | no |

What you would put in a pre-commit hook, what in CI, and what you would run
only before a release:
Pre-commit: `pytest -m "not judged"`. CI: all gates, which re-read the
recorded judgments without a model call. Before a release: a live
`02_judge.py` (about 2 min) and the app batch with `--repeat 2` (41 min).

## The gates

| gate | what it protects | what a failure would mean |
| `test_judge_agrees_with_human_labels`, agreement at least 0.9 | the judge is fit to grade at all | no judged number can be trusted |
| `test_judge_makes_no_false_passes`, false passes 0 | no answer a human failed gets through | a green gate on an invented answer |
| `test_threshold_is_not_on_a_cliff`, at most 0.1 apart within 0.05 | the threshold is not a lucky default | the agreement is an artefact of the threshold |

For each gate, how you made it fail on purpose:
THRESHOLD 0.15 failed the first two (6 of 12, 6 false passes) but not the
cliff gate, since agreement is 0.50 at 0.10, 0.15 and 0.20 alike. THRESHOLD
0.45 failed only the cliff gate (0.75 to 1.00). Two free gates failed for
real on our traces and are marked `xfail(strict=True)` with the reason.

Any gate that asserts a number from this week rather than a property that
should hold for any healthy version, and why you kept it anyway:
None: 0.9 allows one disagreement in twelve, zero false passes holds for
any usable judge, and 0.1 allows one flip. The xfail markers describe
today's traces, and `strict=True` turns them red once the defect is fixed.

## What you will not claim

One paragraph. Name the things your harness does NOT measure, and what
somebody would have to do to find those failures. This paragraph is worth
more marks than a table of good scores, because it is the part that shows
you know where your evidence stops.

Accuracy only means a run ended ok: the 82 ok batch runs were never checked
against the gold set's expected answers. The judge is validated on 12
course-written cases, not on our application's answers, and it is the same
model the app uses for routing and some answers, so self-preference is not
ruled out. The app has no robustness evidence, and predictability does not
see deliberate stops. Finding these needs hand labels on our own answers, a
judge from another model family, and the batch rerun under faults and
paraphrases.
