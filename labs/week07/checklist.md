# Week 7 checklist

## Checkpoint 1, indexed and retrieving

Six items. Do not move to block 2 until all six are true.

- [x] The corpus is chunked, and one chunk printed by hand looks like
      something that could answer a question on its own
- [x] Every chunk still carries its doc_id and its section. Check one.
- [x] The index is built, and you recorded the embedding model, its
      dimensionality, and the chunker settings
- [x] `rank_of_first_gold` and `recall_at_k` are written by you and agree
      with one example you worked out by hand
- [x] `recall_at_k` counts SECTIONS, not chunks, so a long answer split into
      three chunks does not score triple
- [x] All twelve questions retrieve, with results stored to disk rather than
      printed

**If your metrics return the same value on every question**, they are not
measuring anything. That is what happened to the two metrics this session
used to ask for.

## Checkpoint 2, the diagnosis

Six items. Names and ranks, never averages.

- [x] The table reported per question: rank of the first gold chunk for both
      retrievers, and recall at 5
- [x] One sentence saying whether rank one on ten of eleven means the
      pipeline is good or the task is easy
- [x] The question that fails on **both** retrievers named, with a diagnosis
- [x] One sentence on whether any chunk size would fix that question
- [x] The question where dense beats keyword by the most, named, with what
      about it makes meaning beat words
- [x] The gold-set note corrected in `goldset.py`, and the correction
      recorded in `DECISIONS.md`

## Before you leave

- [x] Code committed and pushed
- [x] `python -m project.verify` passes, gold set at 58 cases
- [x] `DECISIONS.md` has all six entries, each carrying the chunker, the
      embedding model, k, and the date

## Homework, before week 8

- [ ] The chunk sweep at 300, 600, 1200, reported by question name
- [ ] This retriever wired into your week 6 memory store's `search`
- [ ] One sentence on what your retrieval measurement still cannot tell you

## What "done" means here

The deliverable is the diagnosis, not the pipeline. A student whose
retrieval scores well and who cannot say why one question fails on both
retrievers has not done the session. A student who names the compositional
limit, explains that no chunk size fixes it, and corrects a false claim in
their own gold set has done it completely.
