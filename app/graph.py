"""Stage: the human approval gate. Replaced in week 8.

Week 8 gates exactly one step, the irreversible one, with a LangGraph
`interrupt` and a checkpoint that a second process resumes. In this
application the irreversible step is submitting a case, and it reaches the
gate through one function:

    request_approval(payload: dict, unattended: bool) -> dict

`payload` has the shape of week 8's interrupt: `action`, `case_id`,
`arguments` (the exact arguments, never a summary a model wrote),
`evidence`, `degraded`, and `missing`. The return value has the shape of
week 8's resume value: `verdict` ("approve", "edit", "reject", or
"timeout"), `by`, and, for an edit, the edited `arguments`.

`unattended` is True in batch mode, which is how week 10 runs the
application. Nobody is there to answer, so your gate must return what week
8 decided an unanswered approval does after its timeout, immediately,
instead of waiting for a human who is not coming.

Until you wire yours in, the gate refuses every submission. That is the
safe default for a stub, and it means nothing irreversible can happen.

This is a stage you write rather than copy, because week 8's graph runs over
its own toy tools. Take your `submit` node from `labs/week08/starter/graph.py`
with its `interrupt` call, give it a small graph and a `SqliteSaver` of its
own, and write `request_approval` around it. Keep week 8's rule: above the
interrupt, read only.
"""

from __future__ import annotations

import getpass
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from project.trace import repo_root

DB = repo_root() / "artifacts" / "approvals.sqlite"

# Week 8 decision: an unanswered approval is not submitted, it is held
# for a person.
TIMEOUT_VERDICT = "timeout"


class GateState(TypedDict):
    payload: dict
    decision: dict


def submit(state: GateState) -> dict:
    # Above the interrupt: read only. Anything here runs twice.
    decision = interrupt(state["payload"])
    return {"decision": decision}


def _build(saver):
    graph = StateGraph(GateState)
    graph.add_node("submit", submit)
    graph.add_edge(START, "submit")
    graph.add_edge("submit", END)
    return graph.compile(checkpointer=saver)


def _ask_a_person(payload: dict) -> dict:
    print("\n  APPROVAL NEEDED:", payload["action"], payload["case_id"])
    print("    arguments:", payload["arguments"])
    print("    evidence: ", payload["evidence"])
    if payload["degraded"]:
        print("    missing:  ", payload["missing"])
    verdict = input("  approve, edit or reject? ").strip().lower()
    decision = {"verdict": verdict, "by": getpass.getuser()}
    if verdict == "edit":
        field = input("  field to change: ").strip()
        value = input("  new value: ").strip()
        decision["arguments"] = {**payload["arguments"], field: value}
    return decision


def request_approval(payload: dict, unattended: bool = False) -> dict:
    if unattended:
        return {"verdict": TIMEOUT_VERDICT, "by": "nobody (unattended)",
                "arguments": payload["arguments"]}
    cfg = {"configurable": {"thread_id": payload["case_id"]}}
    DB.parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(str(DB)) as saver:
        graph = _build(saver)
        out = graph.invoke({"payload": payload, "decision": {}}, cfg)
        asked = out["__interrupt__"][0].value
        out = graph.invoke(Command(resume=_ask_a_person(asked)), cfg)
    return out["decision"]