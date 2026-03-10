from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import quote

import requests

DEFAULT_BASE_URL = "https://gitlab.rnl.tecnico.ulisboa.pt"
DEFAULT_PROJECT_PATH = "es/es26-al-58"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Get a specific GitLab commit and print the API response."
    )
    parser.add_argument("sha", help="Commit SHA")
    parser.add_argument(
        "--token",
        default=os.getenv("GITLAB_TOKEN"),
        help="GitLab private token (default: GITLAB_TOKEN env var)",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"GitLab base URL (default: {DEFAULT_BASE_URL})",
    )
    args = parser.parse_args()

    if not args.token:
        print("Missing token. Use --token or set GITLAB_TOKEN.", file=sys.stderr)
        raise SystemExit(2)

    project = quote(DEFAULT_PROJECT_PATH, safe="")
    sha = quote(str(args.sha), safe="")
    url = f"{args.base_url.rstrip('/')}/api/v4/projects/{project}/repository/commits/{sha}"

    response = requests.get(url, headers={"PRIVATE-TOKEN": args.token}, timeout=15)

    try:
        print(json.dumps(response.json(), indent=2))
    except ValueError:
        print(response.text)


if __name__ == "__main__":
    main()
