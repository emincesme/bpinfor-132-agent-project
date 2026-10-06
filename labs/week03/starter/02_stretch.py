"""Block 4, completed. TODO 8. One variant per group.

    python 02_stretch.py --variant model --replay
    python 02_stretch.py --variant voting --replay

The written answers are at the bottom.
"""

from __future__ import annotations

import argparse
import collections
import time

from queries import QUERIES
from router import apply_policy, classify
from scoring import report, score_routes

from project.models import LARGE, SMALL
from project.trace import write_json

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "compare_mod", Path(__file__).with_name("01_compare.py"))
_cmp = importlib.util.module_from_spec(_spec)
sys.modules["compare_mod"] = _cmp
_spec.loader.exec_module(_cmp)


# --------------------------------------------------------------------------
# TODO 8. One variant. Your instructor assigns you one.
# --------------------------------------------------------------------------

def variant_model(client) -> None:
    """Variant A. Same prompt, same queries, same policy. Only the model.

    Run the classifier over the twenty four queries on SMALL and on LARGE,
    score both, and report per route as counts.

    Report four things per model, not one:
      * route accuracy, and route accuracy excluding the ambiguous four
      * how often the evidence span came back verbatim
      * the minimum and maximum confidence, and how many distinct values
      * the resident memory, which is in project/models.py

    Predict which model wins before you run it, and write the prediction
    down. Then read the confidence range carefully. One of the two models
    tells you something about your threshold from TODO 3a that you cannot
    unsee.
    """
    raise NotImplementedError("TODO 8: variant A, model routing")


def variant_voting(client, k: int = 3) -> None:
    """Variant B. Classify k times at temperature 0.7, majority wins.

    Run sequentially rather than in threads. Your endpoint answers one
    request at a time, so a thread pool buys you nothing here, and finding
    that out is worth more than the speedup you expected.

    Score the majority result, but the number to report is not the accuracy.
    It is the set of queries where the k votes disagreed. Print it, and put
    it next to the list of ambiguous query ids.

    Then ask what that set is worth. Voting costs k times as much for a step
    that was already the cheap one, so as a way to decide it is a poor buy.
    As a way to detect something, it may be a very good one.
    """
    routed, split, metas = [], [], []
    t0 = time.perf_counter()
    for q in QUERIES:
        votes = []
        for _ in range(k):
            decision, meta = classify(client, q.text, temperature=0.7)
            votes.append(decision)
            metas.append(meta)

        routes = [d.route for d in votes if d is not None]
        if len(set(routes)) > 1:
            split.append(q.id)

        chosen = None
        if routes:
            winner = collections.Counter(routes).most_common(1)[0][0]
            chosen = next(d for d in votes if d is not None and d.route == winner)
        routed.append(apply_policy(chosen, q.text))

    print(report(score_routes(routed, QUERIES), "voting, k=3, temperature 0.7"))
    print(f"\nsplit votes: {split}")
    print(f"ambiguous:   {[q.id for q in QUERIES if q.ambiguous]}")
    tokens = sum(m["prompt_tokens"] + m["completion_tokens"] for m in metas)
    print(f"cost: {tokens} tokens, {time.perf_counter() - t0:.1f}s")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=("model", "voting"), required=True)
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    client = _cmp.get_client(args.replay)
    if args.variant == "model":
        variant_model(client)
    else:
        variant_voting(client)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
