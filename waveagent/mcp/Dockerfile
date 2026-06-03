# Hosted WaveAssist MCP server (streamable-HTTP transport).
# Serves the SAME 8 tools as the local stdio server, but over HTTP, with
# per-request auth via the `Authorization: Bearer <WaveAssist-UID>` header
# (multi-tenant). See docs/HOSTING.md.
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Endpoint: http://<host>:$PORT/mcp
ENV WAVEASSIST_MCP_HOST=0.0.0.0 \
    PORT=8000 \
    WAVEASSIST_API_BASE=https://api.waveassist.io \
    WAVEASSIST_APP_BASE=https://app.waveassist.io \
    # Per-user agent registry lives here — mount a persistent volume for durability
    # across redeploys (else re-deploys can't dedup and may create duplicate projects).
    WAVEASSIST_HOME=/data/.waveassist

EXPOSE 8000
CMD ["waveassist-mcp-http"]
