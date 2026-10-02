#!/usr/bin/env python3
"""Real MCP client handshake test against payload-sample-mcp-server over stdio.

Uses the official SDK's ClientSession + stdio_client. All assertions must pass.

Run:  python3 tests/test_handshake.py
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SAMPLE_TEXT = (
    "Model Context Protocol servers expose tools to AI assistants. "
    "Monetizing tools per call is a new business model. "
    "Payload sells kits that help developers charge for tool calls. "
    "This sample demonstrates the free quota mechanic clearly."
)


def text_of(result) -> str:
    return "\n".join(getattr(b, "text", "") for b in result.content)


async def main() -> int:
    failures = []

    def check(label, cond, detail=""):
        status = "PASS" if cond else "FAIL"
        print(f"[{status}] {label}" + (f" -- {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(label)

    import sys as _sys
    _venv_bin = os.path.dirname(_sys.executable)
    env_base = {"PATH": _venv_bin + os.pathsep + os.environ["PATH"]}

    # ---- default quota (5) ----
    params = StdioServerParameters(command="payload-sample-mcp-server", args=[], env=env_base)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            check("initialize", bool(init))
            print(f"         server: {init.server_info.name} v{init.server_info.version}")

            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            check("tools/list returns all 3 tools",
                  names == ["extract_keywords", "summarize", "word_count"], str(names))

            wc = await session.call_tool("word_count", {"text": "hello world\nfoo"})
            wc_text = text_of(wc)
            check("word_count works",
                  "words: 3" in wc_text and "characters: 15" in wc_text and "lines: 2" in wc_text,
                  wc_text)
            check("word_count not error", not wc.is_error)
            for _ in range(2):  # free tool must never consume quota
                r = await session.call_tool("word_count", {"text": "x"})
                assert not r.is_error

            for i in range(5):
                s = await session.call_tool("summarize", {"text": SAMPLE_TEXT, "sentences": 2})
                st = text_of(s)
                check(f"summarize call {i + 1}/5 within quota",
                      not s.is_error and "Model Context Protocol" in st, st[:120])

            s6 = await session.call_tool("summarize", {"text": SAMPLE_TEXT})
            s6_text = text_of(s6)
            check("6th premium call isError", bool(s6.is_error))
            check("6th premium call returns PAYMENT_REQUIRED", "PAYMENT_REQUIRED" in s6_text,
                  s6_text[:120])
            try:
                payload = json.loads(s6_text)
                check("payload is JSON with status PAYMENT_REQUIRED",
                      payload.get("status") == "PAYMENT_REQUIRED")
                check("payload carries quota fields",
                      payload.get("free_quota") == 5
                      and payload.get("premium_calls_used") == 5
                      and "upgrade_url" in payload)
            except json.JSONDecodeError as e:
                check("payload parses as JSON", False, str(e))

            k = await session.call_tool("extract_keywords", {"text": SAMPLE_TEXT})
            check("other premium tool also blocked", bool(k.is_error) and "PAYMENT_REQUIRED" in text_of(k))

    # ---- custom quota via env ----
    params2 = StdioServerParameters(
        command="payload-sample-mcp-server", args=[],
        env={**env_base, "PAYLOAD_FREE_QUOTA": "2"},
    )
    async with stdio_client(params2) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            ok = 0
            for _ in range(2):
                r = await session.call_tool("extract_keywords", {"text": SAMPLE_TEXT, "limit": 5})
                if not r.is_error:
                    ok += 1
            check("PAYLOAD_FREE_QUOTA=2 allows exactly 2 premium calls", ok == 2)
            third = await session.call_tool("extract_keywords", {"text": SAMPLE_TEXT})
            check("3rd premium call blocked under quota=2",
                  bool(third.is_error) and "PAYMENT_REQUIRED" in text_of(third))

    # ---- hard cap via env ----
    params3 = StdioServerParameters(
        command="payload-sample-mcp-server", args=[],
        env={**env_base, "PAYLOAD_HARD_CAP": "2"},
    )
    async with stdio_client(params3) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await session.call_tool("word_count", {"text": "a"})
            await session.call_tool("word_count", {"text": "b"})
            capped = await session.call_tool("word_count", {"text": "c"})
            ct = text_of(capped)
            check("PAYLOAD_HARD_CAP=2 enforced", bool(capped.is_error) and "HARD CAP" in ct, ct[:100])

    print()
    if failures:
        print(f"{len(failures)} FAILURES: {failures}")
        return 1
    print("ALL ASSERTIONS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
