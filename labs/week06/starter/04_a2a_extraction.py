"""My own A2A-style channel: the week 2 extractor as a remote agent.

    PYTHONPATH=.:labs/week02/starter python labs/week06/starter/04_a2a_extraction.py

Week 6 homework. The same three pieces as 03_a2a.py (the card, the task
lifecycle, the artifact), but the remote agent does real work: it runs the
week 2 extractor on a resident's message and returns the validated record
as a data artifact. Failures and timeouts come from real causes, not from
trigger words.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pydantic import ValidationError

from extractor import SYSTEM_ZERO_SHOT, ServiceRequest, extract, get_client

PORT = 8972
OUT = Path("artifacts/week06_a2a.json")

# The card. The skill says what the agent takes and what it gives back:
# plain text in, a JSON record out.
CARD = {
    "name": "extraction-agent",
    "description": "Turns a resident's message into a service request.",
    "url": f"http://127.0.0.1:{PORT}",
    "version": "1.0",
    "skills": [{
        "id": "extract_request",
        "name": "Extract a service request",
        "description": "Reads one message and returns category, urgency, "
                       "due_date and a verbatim quote.",
        "inputModes": ["text/plain"],
        "outputModes": ["application/json"],
    }],
}

# Every task the agent has seen, by id, with its latest state. This is what
# makes a kept task id useful: the caller can ask again later.
TASKS: dict[str, dict] = {}


def run_task(task_id: str, text: str) -> dict:
    """The lifecycle. Every path ends in a terminal state, never a crash."""
    if not text.strip():
        return {"taskId": task_id, "state": "failed",
                "error": "empty message, nothing to extract"}
    try:
        record, meta = extract(get_client(replay=False), SYSTEM_ZERO_SHOT,
                               text)
    except Exception as exc:              # endpoint down, model missing
        return {"taskId": task_id, "state": "failed",
                "error": type(exc).__name__}
    if record is None:                    # the model's JSON failed validation
        return {"taskId": task_id, "state": "failed", "error": meta["error"]}
    return {"taskId": task_id, "state": "completed",
            "artifact": {"parts": [{"data": record.model_dump(mode="json")}]}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/.well-known/agent.json":
            self._send(200, CARD)
        elif self.path.startswith("/tasks/"):
            task_id = self.path.removeprefix("/tasks/")
            self._send(200, TASKS.get(task_id,
                                      {"taskId": task_id, "state": "unknown"}))
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        request = json.loads(self.rfile.read(length) or b"{}")
        text = request.get("message", {}).get("parts", [{}])[0].get("text", "")
        task_id = request.get("taskId", "task-1")
        TASKS[task_id] = {"taskId": task_id, "state": "working"}
        TASKS[task_id] = run_task(task_id, text)
        self._send(200, TASKS[task_id])

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass                          # the caller timed out and left


def serve():
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


# --------------------------------------------------------------------------
# The client side: the help desk delegating to the extraction agent.
# --------------------------------------------------------------------------

def fetch_card() -> dict:
    with urllib.request.urlopen(
            f"http://127.0.0.1:{PORT}/.well-known/agent.json", timeout=5) as r:
        return json.loads(r.read())


def delegate(text: str, task_id: str, timeout: float) -> dict:
    request = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/",
        data=json.dumps({"taskId": task_id,
                         "message": {"parts": [{"text": text}]}}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as r:
        return json.loads(r.read())


def ask_again(task_id: str) -> dict:
    with urllib.request.urlopen(
            f"http://127.0.0.1:{PORT}/tasks/{task_id}", timeout=5) as r:
        return json.loads(r.read())


def read_record(result: dict) -> ServiceRequest | None:
    """The artifact must hold a data part that validates as a record.

    Never stringify what came back: a record that does not validate is
    reported as a mismatch, the same rule as 03_a2a.py's fifth case.
    """
    for part in result.get("artifact", {}).get("parts", []):
        if "data" in part:
            try:
                return ServiceRequest.model_validate(part["data"])
            except ValidationError:
                return None
    return None


MESSAGE = ("The badge reader at the side entrance has not worked since "
           "Monday. Please fix it before 15/11/2026.")


def main() -> int:
    server = mp.Process(target=serve, daemon=True)
    server.start()
    time.sleep(1.5)
    results: dict = {}

    try:
        card = fetch_card()
        skills = [s["id"] for s in card["skills"]]
        print(f"card fetched: {card['name']}, skills {skills}\n")

        # 1. Delegated: the card declares the skill. The record comes back
        #    as a data part and is validated here, not trusted.
        print("1 delegated")
        result = delegate(MESSAGE, "task-1", timeout=60.0)
        record = read_record(result)
        print(f"   -> state {result['state']}, record {record}")
        results["delegated"] = result

        # 2. Not delegated: translation is not on the card, so no request.
        print("\n2 not delegated")
        if "translate" not in skills:
            print("   -> the card declares no 'translate' skill, so this is "
                  "handled locally and no request is sent")
        results["not_delegated"] = "translate is not on the card"

        # 3. Failed: the agent refuses a message with nothing to extract.
        print("\n3 failed")
        result = delegate("   ", "task-3", timeout=60.0)
        print(f"   -> {result}")
        print("   policy: no record is invented; the message goes to a "
              "human queue, marked degraded")
        results["failed"] = result

        # 4. Timed out: a real extraction does not fit in half a second.
        #    The task id is kept, and the client asks again later.
        print("\n4 timed out")
        try:
            result = delegate(MESSAGE, "task-4", timeout=0.5)
            print(f"   -> finished inside 0.5 s: {result['state']}")
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"   -> timeout after 0.5 s ({type(exc).__name__}), "
                  "task id 'task-4' kept")
            result = ask_again("task-4")
            print(f"   asked again at once: {result['state']}")
            for _ in range(30):
                if result["state"] in ("completed", "failed"):
                    break
                time.sleep(2)
                result = ask_again("task-4")
            print(f"   asked again later: {result['state']}, record "
                  f"{read_record(result)}")
        results["timed_out"] = result
    finally:
        server.terminate()

    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"\nwritten to {OUT}")
    return 0


if __name__ == "__main__":
    mp.set_start_method("spawn")
    raise SystemExit(main())
