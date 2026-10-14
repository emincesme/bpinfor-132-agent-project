# Week 5: a planner, an executor, and a second agent

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 5

**Run conditions.** model: qwen2.5:7b (Ollama 0.40.2, context 8192) |
framework: Pydantic AI 2.55.0 | runs per architecture: 3 | served
locally | date: 2026-10-13 | table from: my own runs (the recording
is shown next to them)

### 1. The plan schema

What I tried first, and what happened:

I did not try the nested list of Step objects; the brief reports that it
fails every time. My first version was flat but strict: steps as
list[str] with a schema limit of 2 to 6 items. On the first live run the
planner returned a one-step plan, Pydantic AI retried three times, and
the whole comparison crashed with "Exceeded maximum output retries (3)".
The error does not say that the schema limit was the cause.

What I shipped, and why it is shaped that way:

goal: str, steps: list[str], suspect_file: str, with no limits in the
schema. A flat list of strings is the shallowest shape that still says
"several ordered steps". The step count moved into validate_plan, where
a bad count is recorded instead of crashing the run.

### 2. The validator

| check | what it catches |
| 2 to 6 steps | a plan that skips the fix or wanders (matches the planner's own instruction) |
| suspect_file in KNOWN_FILES | an invented file name |
| a step mentions "run" and "test" | a plan with no way of knowing whether it worked |
| no step names a test file with an edit word | a plan that would edit a test |

On a failed check my system neither repairs nor refuses: it records the
problems and continues, as the starter's propose() does, and an unknown
suspect file falls back to discounts.py. I kept the course design. In my
runs this let the planner's invented file names (bookings.py,
booking_service.py) reach the fixer. The checks are keyword based: "Test
the change to ensure..." was flagged as having no test step.

### 3. The three-way table

| architecture | green | tokens (mean) | seconds (mean) |
| A baseline | 1/3 | 18,755 | 200.9 |
| B planner | 0/3 | 3,577 | 100.7 |
| C planner + reviewer | 0/3 | 2,677 | 97.3 |

C had one crashed run (UnexpectedModelBehavior, recorded as 0 tokens);
over its two finished runs C used 4,016 tokens and 116.0 s. The
recording (2026-08-11) gives A 0/3, B 2/3, C 0/3.

Two changes to get a full table: I set OLLAMA_CONTEXT_LENGTH=8192 as the
course requires (it was unset; crashes fell from 5 of 6 planned runs to
1 of 6), and main_async now counts a crashed attempt as a red run
instead of stopping the script, as the starter already does for the
baseline.

Which I would ship: none as measured (best was A at 1/3). Of the three,
B is the one to build on: it is the cheapest and its failures came from
one cause, the invented file name. Evidence that would change my mind:
B still below A once the planner is given the list of real files.

### 4. Why the baseline fails

What changed between A and B is the width of the action. A can list,
read, replace any line and run tests, in any order, so it wanders: 24,
20 and 14 tool calls, and the only green run was the shortest. B may
only propose one line, which apply_fix checks before anything changes.

In my runs B still failed, for a different reason: the planner is never
shown the repository, yet it must name a suspect file. It invented one
every time, the fixer copied that name into its path, and apply_fix
refused all three with "no such file". Missing information, not
model size.

### 5. The reviewer

Verdicts across my runs: 0 approve, 2 reject (one run crashed first).

Would I ship it: no. Extra cost: about 439 tokens, 15.3 seconds per
run (C's finished runs against B).

Both rejections were the correct fix, > to >=, with reasons like
"changes the comparison operator, affecting the test result". The
reviewer sees only the diff and the failing test, never the rule
"20:00 or later", so it cannot tell a fix from a cheat. Here the test
suite already decides, for free.

The case where it would earn its cost:

A change the tests cannot judge, such as the refactoring in task B, and
only if the reviewer is also given the rule the code must follow.

### 6. What my verifier cannot catch

Changing OFF_PEAK_FROM_HOUR from 20 to 19 makes the suite green. Because
start_hour is a whole hour, "> 19" behaves like ">= 20", so no test can
see the difference, but the constant now says off peak starts at 19:00,
and it would break as soon as bookings start at half hours. Also, the
label in pricing.discount_summary still uses "> 20", and no test covers
that function, so a green suite says nothing about it.

### Deferred

Task B (the refactoring) not attempted yet. Repair once on a failed plan
not implemented. The planner was not given the file list, to keep the
course design. Only three runs per architecture, so the crash rate is
not reliable. The bad patch and wrong-but-passing reviewer tests from
"If you finish early" not done.
