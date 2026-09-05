import os
import sys

from .server import main, serve_http

if __name__ == "__main__":
    _http = "--http" in sys.argv or os.environ.get("WAVEASSIST_MCP_HTTP", "").lower() in ("1", "true", "yes")
    serve_http() if _http else main()
