#!/usr/bin/env python3
"""
Payload Sample MCP Server
=========================

A real, installable MCP server (official ``mcp`` Python SDK, stdio transport)
that demonstrates the core mechanic of Payload's paid MCP Monetization Kit:
per-tool-call metering with a free quota, then a machine-readable
PAYMENT_REQUIRED response once the quota is exhausted.

This is a teaching sample on purpose. The metering is in-memory (resets on
every restart), no real payment is collected, and a hard call cap keeps the
sample from replacing the paid product.

Tools
-----
* word_count       (FREE, unlimited) — count words / characters / lines.
* summarize        (PREMIUM)         — naive extractive summary of text.
* extract_keywords (PREMIUM)         — naive keyword extraction from text.

Metering
--------
* FREE_QUOTA (env PAYLOAD_FREE_QUOTA, default 5): premium tool calls allowed
  before the server starts answering with PAYMENT_REQUIRED.
* HARD_CAP (env PAYLOAD_HARD_CAP, default 200): total calls (free + premium)
  before every call is rejected.

Run it
------
    pip install payload-sample-mcp-server
    payload-sample-mcp-server
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import Counter

from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp import types

SERVER_NAME = "payload-sample-mcp-server"
SERVER_VERSION = "1.0.0"

UPGRADE_URL = "https://payloadtools.gumroad.com/l/mcp-monetization-kit"
READINESS_URL = "https://payloadtools.gumroad.com/l/mcp-launch-readiness-audit"

FREE_QUOTA = int(os.environ.get("PAYLOAD_FREE_QUOTA", "5"))
HARD_CAP = int(os.environ.get("PAYLOAD_HARD_CAP", "200"))

# In-memory meter. A real deployment needs the paid kit's persistent,
# append-only usage ledger (this sample resets on every restart — see README).
premium_calls_used = 0
total_calls = 0


def payment_required_payload(tool_name: str) -> dict:
    """The monetization mechanic: a machine-readable refusal, not a crash."""
    return {
        "status": "PAYMENT_REQUIRED",
        "tool": tool_name,
        "free_quota": FREE_QUOTA,
        "premium_calls_used": premium_calls_used,
        "upgrade_url": UPGRADE_URL,
        "message": (
            "Free quota exhausted (%d/%d premium calls used). "
            "Attach payment to continue, or get the full MCP Monetization "
            "Kit to collect real per-call USDC payments with the x402 flow: %s"
        )
        % (premium_calls_used, FREE_QUOTA, UPGRADE_URL),
    }


TOOLS: list[types.Tool] = [
    types.Tool(
        name="word_count",
        description="Count words, characters, and lines in text. Free and unlimited in this sample.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to analyze"},
            },
            "required": ["text"],
        },
    ),
    types.Tool(
        name="summarize",
        description="Return a short extractive summary of text. PREMIUM: consumes 1 free-quota call.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to summarize"},
                "sentences": {
                    "type": "integer",
                    "description": "Max sentences (default 3)",
                },
            },
            "required": ["text"],
        },
    ),
    types.Tool(
        name="extract_keywords",
        description="Return the most frequent significant words in text. PREMIUM: consumes 1 free-quota call.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to analyze"},
                "limit": {
                    "type": "integer",
                    "description": "Max keywords (default 10)",
                },
            },
            "required": ["text"],
        },
    ),
]

PREMIUM_TOOLS = {"summarize", "extract_keywords"}


def do_word_count(text: str) -> str:
    return "words: %d\ncharacters: %d\nlines: %d" % (
        len(text.split()),
        len(text),
        text.count("\n") + (1 if text else 0),
    )


def do_summarize(text: str, sentences: int = 3) -> str:
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    return " ".join(parts[: max(1, sentences)]) or "(empty input)"


STOPWORDS = set(
    "a an the and or but of to in on for with is are was were be been it its "
    "this that these those as at by from we you they he she his her our your "
    "their not no do does did can will would should could have has had".split()
)


def do_keywords(text: str, limit: int = 10) -> str:
    words = [w.lower() for w in re.findall(r"[a-zA-Z]{3,}", text)]
    counts = Counter(w for w in words if w not in STOPWORDS)
    top = counts.most_common(max(1, limit))
    return "\n".join("%s (%d)" % (w, c) for w, c in top) or "(no keywords found)"


def _text_result(text: str, is_error: bool = False) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        isError=is_error,
    )


async def handle_list_tools(
    ctx: ServerRequestContext,
    params: types.PaginatedRequestParams | None,
) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOLS)


async def handle_call_tool(
    ctx: ServerRequestContext,
    params: types.CallToolRequestParams,
) -> types.CallToolResult:
    global premium_calls_used, total_calls
    name = params.name
    args = params.arguments or {}

    if name not in PREMIUM_TOOLS and name != "word_count":
        return _text_result("Unknown tool: %r" % name, is_error=True)

    # Hard cap: the sample cannot be used as a free service.
    if total_calls >= HARD_CAP:
        return _text_result(
            "HARD CAP REACHED (%d total calls). This sample is capped on purpose. "
            "The full kit has no artificial cap — you set your own prices and quotas: %s"
            % (HARD_CAP, UPGRADE_URL),
            is_error=True,
        )
    total_calls += 1

    if name in PREMIUM_TOOLS:
        if premium_calls_used >= FREE_QUOTA:
            return _text_result(
                json.dumps(payment_required_payload(name), indent=2),
                is_error=True,
            )
        premium_calls_used += 1
        meter_note = "\n\n[metered: %d/%d free premium calls used, %d remaining]" % (
            premium_calls_used,
            FREE_QUOTA,
            FREE_QUOTA - premium_calls_used,
        )
    else:
        meter_note = "\n\n[free tool: no quota consumed]"

    try:
        if name == "word_count":
            out = do_word_count(str(args.get("text", "")))
        elif name == "summarize":
            out = do_summarize(str(args.get("text", "")), int(args.get("sentences", 3)))
        elif name == "extract_keywords":
            out = do_keywords(str(args.get("text", "")), int(args.get("limit", 10)))
        return _text_result(out + meter_note)
    except Exception as exc:  # keep the server alive on bad input
        return _text_result("Tool failed: %s" % exc, is_error=True)


server = Server(
    SERVER_NAME,
    version=SERVER_VERSION,
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool,
)


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    sys.stderr.write(
        "[%s] running on stdio. FREE_QUOTA=%d HARD_CAP=%d.\n"
        % (SERVER_NAME, FREE_QUOTA, HARD_CAP)
    )
    asyncio.run(_run())


if __name__ == "__main__":
    main()
