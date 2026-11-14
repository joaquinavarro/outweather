"""Run ROOTSHIFT with one command: `python -m rootshift`.

Serves the API and, when `frontend/out` exists (built with `npm run build`), the
web app on the same origin. No PowerShell script, no second process at runtime.
"""

from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> None:
    port_env = os.environ.get("PORT")
    default_port = int(port_env) if port_env else 8000
    parser = argparse.ArgumentParser(prog="python -m rootshift", description="ROOTSHIFT server")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (use 0.0.0.0 in Docker)")
    parser.add_argument("--port", type=int, default=default_port, help="port (default 8000 or $PORT)")
    parser.add_argument("--reload", action="store_true", help="auto-reload on code changes (development)")
    args = parser.parse_args()

    uvicorn.run(
        "rootshift.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
