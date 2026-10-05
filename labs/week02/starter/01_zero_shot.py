"""Block 2. The zero-shot baseline, scored per field.

    python 01_zero_shot.py --replay     # the shipped recording, instant
    python 01_zero_shot.py              # your own model, about 45 seconds

Develop your scorer against `--replay`. The recording holds every model
answer for both variants, so your scorer runs in well under a second and you
can iterate on it properly instead of waiting forty-five seconds to find out
you compared the wrong field.

The recording contains real failures, because the model really does make
them. If your scorer reports forty out of forty, your scorer does nothing.

One TODO marker here. TODO 1 to 4 live in extractor.py and scoring.py, and
this file will not run until they are done.
"""

from __future__ import annotations

import argparse

from documents import DOCS, GOLD
from extractor import (PROMPT_VERSION, SYSTEM_ZERO_SHOT, get_client,
                       run_variant)

from project.contracts import GoldCase, GoldSet
from project.trace import write_json

BEHAVIOR = {
    "REQ-01": "extracts category access and urgency urgent, with no due date because the message only says 'tomorrow', a relative expression.",
    "REQ-02": "extracts category hardware and urgency standard, with due date 2026-09-15 converted from the written 15/09/2026.",
    "REQ-03": "extracts category billing and urgency standard, with no due date because the message states none and says there is no hurry.",
    "REQ-04": "extracts category facilities and urgency urgent, with no due date because the message only asks for someone to come immediately.",
    "REQ-05": "extracts category access and urgency standard, with no due date because the message only says 'before the end of the month', a relative expression.",
    "REQ-06": "extracts category billing and urgency info, with no due date because the message is a notice and asks for no action.",
    "REQ-07": "extracts category facilities and urgency standard, with due date 2026-10-01 converted from the date written in words, '1. Oktober 2026'.",
    "REQ-08": "extracts category hardware and urgency urgent, with no due date because the message states none.",
    "REQ-09": "extracts category other and urgency info, with no due date because the message is only a suggestion.",
    "REQ-10": "extracts category access and urgency standard, with no due date because the message only says 'before the end of the month', a relative expression.",
}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true")
    args = ap.parse_args()

    client = get_client(args.replay)
    board, records, metas = run_variant(client, SYSTEM_ZERO_SHOT,
                                        "zero-shot", DOCS, GOLD)

    if board.failures:
        print("failures worth reading:")
        for doc_id, fieldname, note in board.failures[:10]:
            print(f"  {doc_id}  {fieldname:<9} {note}")

    write_json("artifacts/week02_zero_shot.json", {
        "variant": "zero-shot",
        "prompt_version": PROMPT_VERSION,
        "hits": board.hits, "total": board.total, "invalid": board.invalid,
    })

    # TODO 7. Write the gold set into the project spine.
    #
    #   Build a GoldSet out of the ten documents and their annotations and
    #   write it to artifacts/goldset.json with
    #   project.trace.write_json(...).
    #
    #   For each document, one GoldCase with:
    #     case_id           the document id
    #     week_added        2
    #     question          the document text
    #     expected          the gold annotation, as a dict
    #     expected_behavior one sentence a colleague could grade against.
    #                       "extracts category access and urgency standard,
    #                       with no due date because the message only says
    #                       'before the end of the month'" is a good one.
    #                       "works" is not.
    #     slice_tags        at least the language, so week 10 can report per
    #                       language instead of as one average
    #
    #   This is not busywork and it is not for today. Week 3 adds route
    #   labels to this file, week 7 adds retrieval questions, and week 10
    #   builds the evaluation harness on whatever is in it by then. Ten
    #   careful cases now is the cheapest week 10 you will ever have.
    #
    #   Then run: python -m project.verify

    cases = [
        GoldCase(
            case_id=doc.id,
            week_added=2,
            question=doc.text,
            expected={"category": GOLD[doc.id].category,
                      "urgency": GOLD[doc.id].urgency,
                      "due_date": GOLD[doc.id].due_date},
            expected_behavior=BEHAVIOR[doc.id],
            slice_tags=[doc.lang],
        )
        for doc in DOCS
    ]
    write_json("artifacts/goldset.json", GoldSet(cases=cases).model_dump())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
