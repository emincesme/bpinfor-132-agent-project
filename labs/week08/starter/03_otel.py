"""Homework: one run wrapped in OpenTelemetry spans.

    python 03_otel.py

One case through the week 8 graph, with faults chosen so that a retry
(fees:flaky), a fallback (search:timeout) and the gate all happen. Every
call through the retry ladder becomes a span, every attempt an event on
it, and the gate is a span of its own.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter)

import graph
from faults import FaultPlan

exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("week08")

ladder = graph.call_with_policy


def traced_ladder(fn, *args, **kwargs):
    """The same retry ladder, with one span per call."""
    with tracer.start_as_current_span(f"step:{fn.__name__}") as span:
        res = ladder(fn, *args, **kwargs)
        for a in res.attempts:
            span.add_event("attempt", {"n": a.n, "error": a.error or "none"})
        span.set_attribute("tries", res.tries)
        span.set_attribute("used_fallback", res.used_fallback)
        span.set_attribute("outcome", res.outcome)
        return res


graph.call_with_policy = traced_ladder


def show(span, children, depth=0):
    print("  " * depth + span.name, dict(span.attributes))
    for event in span.events:
        print("  " * (depth + 1) + f"- {event.name} {dict(event.attributes)}")
    for child in children.get(span.context.span_id, []):
        show(child, children, depth + 1)


def main() -> int:
    plan = FaultPlan.parse("search:timeout@1.0,fees:flaky@1.0", seed=42)
    cfg = {"configurable": {"thread_id": "otel-demo"}}
    g = graph.build(plan, InMemorySaver())

    with tracer.start_as_current_span("case RB-2026-0042"):
        out = g.invoke(graph.initial("RB-2026-0042", "parking vignette"), cfg)
        with tracer.start_as_current_span("gate") as gate:
            gate.set_attribute("action", out["__interrupt__"][0].value["action"])
            out = g.invoke(Command(resume={"verdict": "approve",
                                           "by": "a.muller"}), cfg)
            gate.set_attribute("verdict", out["decision"])
            gate.set_attribute("submitted", out["submitted"])

    spans = exporter.get_finished_spans()
    children = {}
    for span in spans:
        if span.parent is not None:
            children.setdefault(span.parent.span_id, []).append(span)
    for span in spans:
        if span.parent is None:
            show(span, children)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())