# One-command demo of the paywall mechanic, no Python environment needed:
#   docker build -t payload-sample-mcp-server .
#   docker run -i --rm payload-sample-mcp-server
# Speaks JSON-RPC over stdio, exactly like the local `payload-sample-mcp-server` command.
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY payload_sample_mcp_server ./payload_sample_mcp_server
RUN pip install --no-cache-dir .
CMD ["payload-sample-mcp-server"]
