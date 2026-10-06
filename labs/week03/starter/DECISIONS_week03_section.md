# Week 3: a router in front of the extractor

Copy this into your `DECISIONS.md` and fill it in.

---

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

- The `request` specialist uses the week 2 zero-shot prompt through the
  free-text `respond()` call, so it returns prose rather than a validated
  `ServiceRequest`. Wiring the week 2 extractor (the shipped few-shot
  variant) behind this route is homework.
- Model routing (variant A) was not run: a second, larger model does not
  fit alongside the first on an 8 GB machine.
- The route definition I would rewrite first is `info`, limited to
  questions about the help desk's own services; I expect `other -> info`
  to drop.
