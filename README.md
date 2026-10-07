<!-- mcp-name: io.github.payloadhq/payload-sample-mcp-server -->

# Payload Sample MCP Server by Payload

**A free sample by Payload** - companion to the
[MCP Monetization Kit](https://payloadtools.gumroad.com/l/mcp-monetization-kit).

A real, installable [MCP](https://modelcontextprotocol.io) server (official
`mcp` Python SDK, stdio transport) that demonstrates **the core mechanic of
Payload's paid MCP Monetization Kit**: per-tool-call metering with a free
quota, then a machine-readable `PAYMENT_REQUIRED` response once the quota is
exhausted.

Small software that earns its keep.

## What it does

| Tool | Tier | What it does |
|------|------|--------------|
| `word_count` | **FREE, unlimited** | Count words, characters, and lines of input text. |
| `summarize` | **PREMIUM** | Naive extractive summary of text. |
| `extract_keywords` | **PREMIUM** | Naive keyword extraction from text. |

## The free-quota mechanic

Premium tools get a free quota (default **5 calls**, env `PAYLOAD_FREE_QUOTA`).
After that, the server answers with a machine-readable x402-style
`PAYMENT_REQUIRED` JSON payload - it does **not** crash, and it collects
**no real payment**:

```json
{
  "status": "PAYMENT_REQUIRED",
  "tool": "summarize",
  "free_quota": 5,
  "premium_calls_used": 5,
  "upgrade_url": "https://payloadtools.gumroad.com/l/mcp-monetization-kit",
  "message": "Free quota exhausted (5/5 premium calls used). Attach payment to continue, or get the full MCP Monetization Kit to collect real per-call USDC payments with the x402 flow: ..."
}
```

A hard cap (default **200 total calls**, env `PAYLOAD_HARD_CAP`) keeps this
sample from being used as a free service. Metering is in-memory and resets on
every restart.

## Install + run

Requires Python 3.10+.

```bash
git clone https://github.com/Payloadhq/payload-sample-mcp-server
cd payload-sample-mcp-server
pip install -e .
payload-sample-mcp-server
```

### Use it in Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "payload-sample": {
      "command": "payload-sample-mcp-server"
    }
  }
}
```

### Use it in Cursor

Add to your Cursor MCP settings (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "payload-sample": {
      "command": "payload-sample-mcp-server"
    }
  }
}
```

## What's deliberately missing (the paid kits)

This sample **proves the monetization mechanic works**. It does not replace
the paid products:

- **Real payment collection.** The [**MCP Monetization Kit** ($69)](https://payloadtools.gumroad.com/l/mcp-monetization-kit) collects actual per-call USDC payments via the x402 flow, with two verifiers (HMAC dev verifier for testing, facilitator verifier for production) - non-custodial, it verifies payment then runs your tool. It ships a paid tool registry (registerTool / callTool / listTools) with per-tool pricing, free-quota logic, an append-only usage ledger, the official SDK adapter over the stdio transport, 15 automated tests, and a working example server and paying example client.
- **Security hardening.** The sample is intentionally unauthenticated. The [**MCP Launch Readiness Audit** ($79)](https://payloadtools.gumroad.com/l/mcp-launch-readiness-audit) gives you a 48-rule scanner with concrete fixes, hardened server templates (Python and TypeScript) with bearer-token auth, per-tool scopes and rate limits, a reliability stress-test harness, a deployment readiness verifier, CI wiring, a regression suite, and a branded audit PDF report.
- **Paid APIs over x402.** The [**Veyline Developer Primer** ($79)](https://payloadtools.gumroad.com/l/x402-paid-api-starter-kit) (formerly the x402 Paid API Starter Kit) charges AI agents per API call in USDC: paid-route middleware, `/.well-known/x402` manifest generator, HMAC + facilitator verifiers, append-only usage ledger, working example server, 46 automated tests. Non-custodial by design.

## Payload ecosystem

- **All Payload products** - https://payloadtools.gumroad.com
- **More Payload repos** - https://github.com/Payloadhq

Support: kylers.partners@gmail.com · "Small software that earns its keep."

## License

MIT - see [LICENSE](LICENSE).

---

**Payload** - small, sharp tools for developers.
Developer portal: https://payloadhq.github.io/ ·
All products: https://payloadtools.gumroad.com/ ·
Contact: kylers.partners@gmail.com
