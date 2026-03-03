"""Simple GitLab GET debugger.

Set your token once:
    export GITLAB_TOKEN=glpat-...

Optional (defaults shown):
    export GITLAB_URL=https://gitlab.com

Examples:
    python scripts/gitlab_api_experiments.py /user
    python scripts/gitlab_api_experiments.py /projects/15/issues --param state=opened --param labels=bug
    python scripts/gitlab_api_experiments.py /projects/15 --show-headers
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv


def _json_print(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _parse_key_values(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Expected key=value, got: {item}")
        key, val = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Empty key in: {item}")
        parsed[key] = val
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GitLab API GET debugger")
    parser.add_argument(
        "path",
        help="GitLab API path under /api/v4 (e.g. /user or /projects/15/issues)",
    )
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Query param in key=value form (repeatable)",
    )
    parser.add_argument(
        "--token",
        default="",
        help="GitLab token override (otherwise uses GITLAB_TOKEN)",
    )
    parser.add_argument(
        "--url",
        default="",
        help="GitLab base URL override, e.g. https://gitlab.com (otherwise uses GITLAB_URL)",
    )
    parser.add_argument(
        "--show-headers",
        action="store_true",
        help="Print response headers",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print raw text instead of pretty JSON",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: 30)",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Load variables from .env (searches current directory and parents)
    load_dotenv()

    token = (args.token or os.getenv("GITLAB_TOKEN", "")).strip()
    if not token:
        parser.error("Missing GitLab token. Set GITLAB_TOKEN or pass --token.")

    gitlab_url = (args.url or os.getenv("GITLAB_URL", "https://gitlab.com")).rstrip("/")
    base_url = f"{gitlab_url}/api/v4"

    path = args.path.strip()
    if not path.startswith("/"):
        path = f"/{path}"

    params = _parse_key_values(args.param)

    with httpx.Client(
        base_url=base_url,
        headers={"PRIVATE-TOKEN": token},
        timeout=args.timeout,
    ) as client:
        response = client.get(path, params=params or None)

    print(f"Status: {response.status_code}")
    print(f"URL: {response.request.url}")

    if args.show_headers:
        print("Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")

    print("Body:")
    if args.raw:
        print(response.text)
        return

    try:
        _json_print(response.json())
    except ValueError:
        print(response.text)


if __name__ == "__main__":
    main()
