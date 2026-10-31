"""Week 5 homework, task B: the refactoring, on the same three architectures.

    PYTHONPATH=.:labs/week05/starter python labs/week05/starter/02_task_b.py --runs 1

The four discount rates are written out by hand in twelve places across
discounts.py, pricing.py and report.py. Task B makes them all come from the
four constants at the top of discounts.py. There is no failing test to
guide it, so "done" is measured here: no rate written out by hand, and the
suite still green.

Three decisions, recorded in DECISIONS.md:
  1. Every run starts from a copy with the task A fix applied, so the suite
     starts green.
  2. B and C may change one line per round. They get up to MAX_ROUNDS
     rounds, each with the current list of lines still to change.
  3. C's reviewer is shown the task B rule next to the diff.
"""

from __future__ import annotations

import argparse
import asyncio
import time
import traceback

from agents import baseline, propose, reviewer
from repo import Work, apply_fix, diff_summary, run_tests

from project.trace import TraceRecorder, local_conditions, write_json

MAX_ROUNDS = 20

TASK_B = (
    "Refactor, do not fix a bug: every test already passes. The four "
    "discount rates (resident 10 percent, off peak 20 percent, club 15 "
    "percent, cap 30 percent) are written out by hand: as numbers inside "
    "the functions of discounts.py, and as text such as '10%' in "
    "pricing.py and report.py. Make every one of them come from the four "
    "constants at the top of discounts.py: RESIDENT_RATE, OFF_PEAK_RATE, "
    "CLUB_RATE and MAX_TOTAL_DISCOUNT. A label can be built with "
    "f\"{RESIDENT_RATE:.0%}\", which gives 10%. Keep every test passing. "
    "Do not change any test file.")

RATE_NUMBERS = ("0.10", "0.20", "0.15", "0.30")
RATE_TEXTS = ("10%", "20%", "15%", "30%")
CONSTANTS = ("RESIDENT_RATE =", "OFF_PEAK_RATE =", "CLUB_RATE =",
             "MAX_TOTAL_DISCOUNT =")


def duplicates(work: Work) -> list[str]:
    """Every line that still writes a rate out by hand: the measure of done.

    The four constant definitions in discounts.py are the one place a rate
    may be written. Comments do not count.
    """
    found = []
    for path in ("discounts.py", "pricing.py", "report.py"):
        for n, line in enumerate(work.read(path).splitlines(), start=1):
            code = line.split("#")[0]
            if path == "discounts.py" and code.strip().startswith(CONSTANTS):
                continue
            if any(t in code for t in RATE_NUMBERS + RATE_TEXTS):
                found.append(f"{path}:{n}: {line.strip()}")
    return found


def start() -> Work:
    """A fresh copy with the task A fix applied, so the suite starts green."""
    work = Work.fresh()
    apply_fix(work, "discounts.py", "return start_hour > OFF_PEAK_FROM_HOUR",
              "return start_hour >= OFF_PEAK_FROM_HOUR")
    return work


def task_with(left: list[str]) -> str:
    return TASK_B + "\nStill written out by hand:\n" + "\n".join(left)


def finish(arch: str, index: int, work: Work, t0: float, tokens: int,
           **extra) -> dict:
    """Measure the result, write a trace, clean up, return the row."""
    left = duplicates(work)
    tests = run_tests(work)
    row = {"architecture": arch, "run": index,
           "duplicates_left": len(left), "green": tests.passed,
           "done": not left and tests.passed, "tokens": tokens,
           "seconds": round(time.perf_counter() - t0, 1), **extra}
    rec = TraceRecorder(
        week=5, case_id=f"taskB-{arch}-run{index}",
        conditions=local_conditions("qwen2.5:7b", temperature=0.0,
                                    architecture=arch, task="B"),
        user_input=TASK_B)
    with rec.step("check", "duplicates_and_tests") as span:
        span.detail(duplicates_left=len(left), green=tests.passed)
    rec.finish(output=f"{len(left)} duplicates left",
               outcome="ok" if row["done"] else "error",
               duplicates_left=len(left), green=tests.passed)
    work.cleanup()
    return row


async def run_baseline(index: int) -> dict:
    work = start()
    t0 = time.perf_counter()
    tokens = calls = 0
    error = None
    try:
        r = await baseline.run(task_with(duplicates(work)), deps=work)
        calls = sum(1 for m in r.all_messages() for p in m.parts
                    if getattr(p, "tool_name", None))
        tokens = r.usage.total_tokens or 0
    except Exception as exc:                                  # noqa: BLE001
        error = type(exc).__name__
        print(f"    baseline run {index} raised {error}")
    return finish("A baseline", index, work, t0, tokens,
                  tool_calls=calls, error=error)


async def run_planned(index: int, with_reviewer: bool, rounds: int) -> dict:
    arch = "C planner+reviewer" if with_reviewer else "B planner"
    work = start()
    t0 = time.perf_counter()
    tokens = 0
    log = []
    crashes_in_a_row = 0
    for n in range(1, rounds + 1):
        left = duplicates(work)
        if not left and run_tests(work).passed:
            break
        try:
            out = await propose(work, task_with(left), use_plan=True)
            fix = out["fix"]
            tokens += out["tokens"]
            verdict = None
            if with_reviewer:
                diff = diff_summary(work, fix.path, fix.old_line, fix.new_line)
                r = await reviewer.run(f"Task:\n{TASK_B}\n\n"
                                       f"Proposed change:\n{diff}\n\n"
                                       f"Test output:\n{run_tests(work).output}")
                verdict = r.output
                tokens += r.usage.total_tokens or 0
            if verdict is None or verdict.decision == "approve":
                applied = apply_fix(work, fix.path, fix.old_line, fix.new_line)
            else:
                applied = "rejected by reviewer: " + verdict.reason
        except Exception as exc:                              # noqa: BLE001
            # Which line of ours or of agents.py was running when it failed
            where = [f.line for f in traceback.extract_tb(exc.__traceback__)
                     if f.filename.endswith(("agents.py", "02_task_b.py"))]
            error = (f"{type(exc).__name__} at {where[-1] if where else '?'}: "
                     f"{exc}")[:200]
            print(f"    {arch} run {index} round {n} raised {error}")
            log.append({"round": n, "applied": "crashed", "error": error})
            crashes_in_a_row += 1
            if crashes_in_a_row == 3:
                break
            continue
        crashes_in_a_row = 0
        log.append({"round": n, "applied": applied[:120],
                    "fix": f"{fix.path}: {fix.old_line.strip()} -> "
                           f"{fix.new_line.strip()}"[:160]})
    crashed = sum(1 for entry in log if entry["applied"] == "crashed")
    return finish(arch, index, work, t0, tokens, rounds_used=len(log),
                  crashed_rounds=crashed, rounds=log)


async def main_async(runs: int, rounds: int) -> list[dict]:
    rows = []
    for i in range(1, runs + 1):
        rows.append(await run_baseline(i))
        for with_reviewer in (False, True):
            rows.append(await run_planned(i, with_reviewer, rounds))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--rounds", type=int, default=MAX_ROUNDS)
    args = ap.parse_args()

    work = start()
    print(f"start: {len(duplicates(work))} rates written out by hand, "
          f"tests green: {run_tests(work).passed}\n")
    work.cleanup()

    rows = asyncio.run(main_async(args.runs, args.rounds))

    print(f"\n{'architecture':<22}{'run':>4}{'left':>6}{'green':>7}"
          f"{'rounds':>8}{'tokens':>9}{'seconds':>9}")
    print("-" * 65)
    for r in rows:
        print(f"{r['architecture']:<22}{r['run']:>4}{r['duplicates_left']:>6}"
              f"{str(r['green']):>7}{str(r.get('rounds_used', '-')):>8}"
              f"{r['tokens']:>9}{r['seconds']:>9.1f}")

    write_json("artifacts/week05_task_b.json",
               {"max_rounds": args.rounds, "rows": rows})
    print("\nwritten to artifacts/week05_task_b.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
