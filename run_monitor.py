"""Daemon entrypoint for the CRE Signal Agent Phase B monitor loop."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from dotenv import load_dotenv


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="CRE Signal Agent monitor daemon.")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run one full pipeline cycle immediately before starting the 8am scheduler.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    from src.agents.monitor import start_monitor

    start_monitor(run_now=args.run_now)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
