"""Block 2, first half: call the memory tools over MCP. TODO 6.

    python mcp_server.py &          # in one terminal
    PORT=8001 python mcp_server.py & # and a second instance
    python 01_mcp_client.py

Three things happen here and the third is the one to watch.
"""

from __future__ import annotations

import asyncio

from mcp.client import Client

SUBJECT = "A. Muller"


def text_of(result) -> str:
    content = getattr(result, "content", result)
    if isinstance(content, list) and content:
        return getattr(content[0], "text", str(content[0]))
    return str(content)


async def call(port: int, tool: str, **args):
    async with Client(f"http://127.0.0.1:{port}/mcp") as client:
        return await client.call_tool(tool, args)


async def main() -> int:
    """TODO 6. Three steps, and the third has a warning attached.

    1. Connect to :8000 and print the tool catalog. Seeing it arrive over
       HTTP is what makes the boundary real: these tools are not in this
       process.

    2. Call open_case and then remember on :8000. Watch
       artifacts/memory_store.json change while it runs.

    3. Redeem the SAME handle on :8001, the second instance, and recall from
       it.

    The warning: step 3 on its own does not prove the protocol is stateless.
    It would work under the old session-based protocol too, because each
    call opens its own connection and the state is on disk. It shows that a
    file is a file. 02_stateless.py is the demonstration that actually
    distinguishes the two, and it is the next thing you run.
    """
    # 1. The catalog, discovered over HTTP. Revision 2026-07-28: no
    #    initialize handshake, every request describes itself.
    async with Client("http://127.0.0.1:8000/mcp") as client:
        tools = await client.list_tools()
    print("tools on 8000:", [t.name for t in getattr(tools, "tools", tools)])

    # 2. Mint a case handle and write a fact on the first instance
    handle = text_of(await call(8000, "open_case", subject=SUBJECT))
    print("case handle from 8000:", handle)
    fact_handle = text_of(await call(8000, "remember", subject=SUBJECT,
                                     kind="contact", fact="Prefers email only"))
    print("fact handle from 8000:", fact_handle)

    # 3. Redeem the SAME case handle on the second instance
    subject = text_of(await call(8001, "case_subject", handle=handle))
    print("case_subject on 8001:", subject)
    facts = await call(8001, "recall", subject=subject, query="email")
    print("recall on 8001:", text_of(facts))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
