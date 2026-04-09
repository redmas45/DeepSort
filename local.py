from __future__ import annotations

import argparse
import threading
import webbrowser

import uvicorn

from backend.app.core.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DeepSORT locally with the built-in frontend.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the local server to.")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind the local server to.")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload mode.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open the app in the default browser.",
    )
    return parser.parse_args()


def open_browser(url: str) -> None:
    webbrowser.open(url, new=1)


def main() -> None:
    args = parse_args()
    settings = get_settings()
    settings.video_dir.mkdir(parents=True, exist_ok=True)

    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        threading.Timer(1.2, open_browser, args=[url]).start()

    print(f"Starting DeepSORT locally at {url}")
    print("The plain frontend is served directly by FastAPI. No Node build is required.")

    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
