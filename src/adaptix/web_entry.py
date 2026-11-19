"""`adaptix-web` — serve the ADAPTIX web UI locally.

Thin dispatch, same spirit as ``ui_entry.py``: no argument parsing beyond host/port,
everything else comes from `.env` exactly like the CLI and the TUI.
"""
import os
import sys


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    host = os.getenv('ADAPTIX_WEB_HOST', '127.0.0.1')
    port = int(os.getenv('ADAPTIX_WEB_PORT', '8420'))
    if argv:
        host = argv[0]
    if len(argv) > 1:
        port = int(argv[1])
    from src.adaptix.web.app import main as web_main
    web_main(host=host, port=port)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
