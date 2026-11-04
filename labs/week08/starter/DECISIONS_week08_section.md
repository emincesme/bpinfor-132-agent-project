# Week 8: retries, recovery, and a human approval gate

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 8

**Run conditions.** fault seed: 42 | attempts: 3 | base delay: 0.02 s
(01_survive.py), 0.05 s (graph.py) | max elapsed: 3.0 s | LangGraph
1.2.19, langgraph-checkpoint-sqlite 3.1.3 | no model in blocks 1 to 3 |
date: 2026-11-04

### 1. Which errors are retryable

Retryable: ToolTimeout, RateLimited and ServerError. They say the
upstream is having a moment, so the same call a little later can
succeed: on flaky the second attempt passed.

Deliberately NOT retryable: ContractDrift, because the call succeeded
and the answer is valid, only a field was renamed. Retrying a call that
succeeded returns the same wrong answer every time and only costs time.
Every other exception is not retryable either, for example a bug in my
own code, which fails the same way on every attempt.

### 2. The fault matrix

| | correct | WRONG | degraded | failed |
| baseline | 1 | 0 | 2 | 5 |
| hardened | 2 | 0 | 5 | 1 |

What hardening actually bought:

Not more correct answers: only flaky moved to correct, because its
second attempt succeeded. Hardening took the failed column from 5 to 1
by turning four failures into degraded answers that say what is
missing: search fell back to the cached copy and the fee is named as
missing. WRONG stayed at 0. On drift the fee step reports one attempt,
not three: validate_fee raises ContractDrift and the ladder skips the
retries.

### 3. The empty result

An empty result is not an error. My pipeline treats it as "not
covered": the answer is marked degraded and says that the handbook does
not cover the topic, because treating it as a success lets the model
answer from nothing. For the fee, an empty record has no fee_eur, so
validate_fee rejects it and the fee is named as missing.

### 4. The gate

Gated step: submit. The others are not gated because gather and price
only read, and draft writes text nobody has seen yet, so their mistakes
can be redone. Gating them would train the approver to click through.
submit sends the case into the commune's system, possibly with a
letter, which is hard to undo.

An unanswered approval after the timeout: not submitted, held for a
person (verdict "timeout"). That protects the resident from a case or a
letter sent without review. The cost is a delay, which is cheaper to fix
than a wrong submission.

The approval payload carries the exact arguments, the evidence, whether
the answer is degraded and what is missing, and deliberately does not
carry the drafted text: the approver should check the real values, not
a summary written by the system being checked.

Resumed from a second process: `02_gate.py start` paused at submit and
exited; `resume approve`, `edit` and `reject` each ran in a new process
from artifacts/week08_runs.sqlite. Edit submitted the edited fee (55.0),
not the original (60.0); reject submitted nothing.

### 5. The duplicate the state does not show

I put a side effect above the interrupt: a "letter sent" line written to
a file. It executed 2 times, once before the pause and once on resume,
because the node re-executes from its first line. The recorded state
showed it 0 times: side_effects held only "SUBMITTED RB-2026-0042".

What that means for anything my gated node does before it asks:

it must only read. Anything that writes, sends or pays goes after the
interrupt, where it runs once. A run with a write above the interrupt
looks clean in the state and still sent the letter twice. I removed
the experiment after the run.

### Wired into app/

- retry.py and faults.py copied into app/, import made relative. The
  policies in pipeline.py are kept: memory search 3 attempts within
  3 s, then degrade; the agent 2 attempts within 60 s, then degrade,
  because one agent run takes 15 to 25 s on this machine.
- app/graph.py: request_approval wraps a one-node LangGraph graph with
  my submit node and its own SqliteSaver (artifacts/approvals.sqlite).
  Unattended, it returns "timeout" at once, so nothing is submitted.
  Attended, it pauses at the interrupt, asks in the terminal (approve,
  edit one field, or reject) and resumes; any other answer submits
  nothing.
- Proof, 2026-11-04, qwen3:4b-instruct: `--unattended --route request`
  ended "Not submitted: the approval gate answered timeout" (blocked);
  attended with approve, "Logged a access request, urgency urgent"
  (ok); a typing slip ("aproveapprove") submitted nothing. `--batch` on
  the first 3 gold cases finished with nobody present: blocked 3,
  error 0.

### Still open

- is_retryable knows only the lab's fault classes. A real failure in
  app/, such as an error from the openai client when Ollama does not
  answer, is not on the list, so it degrades at once without a retry.
- The approver sees the three corpus chunks from memory.search as
  evidence even when they are unrelated: a badge reader request showed
  civil status, residence certificate and parking fee chunks. Dense
  search has no similarity threshold.
- In app/, attended approval is asked and resumed in the same process;
  the checkpoint would allow a resume from another process, but app.run
  has no resume command.
- The full --batch over 58 gold cases has not been run yet (about 30 to
  60 minutes on this machine).

### Homework: OpenTelemetry trace

`labs/week08/starter/03_otel.py` runs one case through the week 8 graph
with search:timeout and fees:flaky (opentelemetry-sdk, 2026-11-04).
Every call through the retry ladder becomes a span and every attempt an
event on it, by wrapping call_with_policy, so graph.py is unchanged; the
gate is a span of its own. The trace, in
`artifacts/week08_otel_trace.txt`, shows the fallback (search, 3 tries,
used_fallback True), the retry (fees, 2 tries, ok) and the gate
(approve, submitted). The spans are kept in memory and printed, not
sent to a collector.

### Deferred

- Homework, timeout: built in app/ as the unattended path, proved
  above. A timer that waits a set time for a person is not built.
- What my fault harness cannot simulate: a response with the right
  shape and a wrong value, for example a fee of 6.00 instead of 60.00.
  validate_fee checks the shape only, so it would pass and the answer
  would be WRONG. No fault in the harness produces one, which is also
  why WRONG stayed at 0 in both runs.
- Stretch: the gate firing with no human present is shown by the
  unattended run, not by an automated test.