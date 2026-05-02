"""CLI entrypoint for the Phase A CRE Signal Agent demo."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from dotenv import load_dotenv
from src.pipeline.briefs import render_brief
from src.pipeline.demo import parse_zips_argument, render_digest, run_demo_for_zips


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run the CRE Signal Agent Phase A demo.")
    parser.add_argument(
        "--zips",
        required=True,
        help="Comma-separated ZIP codes, e.g. 10001,60601,90210",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        zip_codes = parse_zips_argument(args.zips)
        result = run_demo_for_zips(zip_codes)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    for failure in result.failures:
        print(f"Skipping ZIP {failure.zip_code}: {failure.reason}", file=sys.stderr)

    if not result.digest:
        print("No Gold records were produced.", file=sys.stderr)
        return 1

    print(render_digest(result.digest))
    if result.brief is not None:
        print()
        print(render_brief(result.brief))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
