# Week 6: memory, a stateless MCP server, and an A2A channel

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 6

**Run conditions.** MCP SDK version: 2.0.0rc1 | specification revision:
2026-07-28 | model: none, no model was called this week | served
locally | date: 2026-10-20

### 1. The handle

Format I chose: `fact-` followed by 12 random hex characters from
`secrets.token_hex(6)`, for example `fact-7645c803497f`. Same pattern as
the course's `open_case`.

A guessable handle would expose: a sequential handle such as `fact-0007`
shows how many facts the store holds, and lets anyone who sees one handle
try its neighbours (`fact-0006`) to read or forget another resident's
fact. A random handle stops the guessing, but whoever holds a handle can
still use it. The authorization check is homework.

Without a handle, the server would have to remember between calls
which resident a conversation is about, tied to a session. With a second
instance behind a load balancer, the next request can land on the
instance that never saw that session, so it would need sticky sessions
or a shared session store. With the handle, every request says what it
is about, so any instance can answer it.

### 2. Conflict and retention

- A write that contradicts an older fact: overwrite. A new fact with the
  same subject and kind replaces the older one, because the code, not
  the model, should decide which fact is current. In earlier weeks the
  model was unreliable when it had to choose between unclear
  information. The cost: the history of what changed is lost, the
  handle changes, and kind must stay narrow ("contact", not "note") or
  unrelated facts overwrite each other.
- How long a record lives: no automatic expiry. A fact lives until
  `forget` deletes it. I kept it that way on purpose: the right period
  depends on the kind of data and on the law (GDPR asks to keep
  personal data no longer than necessary), so the commune and its legal
  team should set it, not the developer. An invented number such as 90
  days would be a decision without a reason. A real service needs a
  period per kind, or deletion when the case is closed.

### 3. What k costs

k = 3. Tokens added per call: about 25 with today's facts (91
characters as a JSON list, at about 4 characters per token). This is
an estimate, not a measurement: no model was called this week. Each
fact adds roughly 8 tokens, so the cost grows with k and with how long
the facts are, not with the size of the store. For comparison, the five
tool descriptions alone are about 330 tokens (same estimate) and travel
with every model request, so the catalog costs more than k does.

At four hundred facts in the store, this design still sends at most k
facts per call, because search is scoped to one subject and capped at
k. What grows is everything around it: every tool call reads and parses
the whole JSON file, search scans every fact to find the subject's, and
every write rewrites the whole file. Two instances writing at the same
moment can also lose an update, because each saves its own copy over
the other's. A real store would need a database with indexes and
locking.

### 4. Memory off against memory on

Deferred. Nothing in this week's material calls a model: blocks 1 to 3
call the tools directly from scripts, so there are no measured tokens
or turns for either side. Measuring it needs an agent loop, like week
4's, wired to the MCP tools and a model. No TODO asks for that and I
did not build it this week. What I expect, not measured: memory on adds
the recalled facts (about 25 tokens at k = 3, estimate) and the tool
catalog to every call, and saves the turns the agent would otherwise
spend asking the resident again for what they already said.

### 5. The protocol, at the wire

| server mode | status | Mcp-Session-Id | answered |
| stateless_http=True | 200 | none | yes |
| stateless_http=False | 400 | present | no |

The error the session-mode server returned, quoted exactly:

`{"jsonrpc":"2.0","id":null,"error":{"code":-32600,"message":"Bad Request: Missing session ID"}}`

Why the two-server handle demonstration does not prove this on its own:

The handle resolved on the second instance because both instances read
the same `artifacts/memory_store.json`, and because the client opened a
new connection for every call (a new client port each time in the
server logs). In session mode each new connection would get its own
session, so no session ever had to travel between instances, and the
case would still be found in the shared file. That demonstration passes
with statelessness switched off, so it only shows that a file is a
file. The raw request above fails in session mode, which is what makes
it a proof.

### 6. What forget does not reach

`forget` deletes the fact from the store, so it no longer comes back in
any later search, on any server instance. It cannot delete copies made
before: a running conversation where the model already saw the fact,
logs and traces, backups, and the git history once
`artifacts/memory_store.json` is committed. For a resident who asks to
be deleted, `forget` is necessary but not enough, and telling them
"deleted" after `forget` alone would not be fully true.

### Deferred

- Entry 4, memory off against memory on: not measured, because no
  script this week calls a model (see entry 4).
- Homework before week 7: build the A2A channel from the marked
  sections, and add an authorization check on the handle. Today anyone
  holding a handle can read the case.
