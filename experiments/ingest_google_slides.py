"""Read one Google Slides presentation into schema 1.0 JSON.

Run from the repository root: python3 -m experiments.ingest_google_slides
Tokens come only from the environment. No content is printed or sent to inference.
"""
import argparse
import os
import sys
from pathlib import Path

from presentation.adapters.google_slides import GoogleSlidesSource
from presentation.model import deck_to_json
from presentation.source import PresentationSourceError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("presentation_id")
    parser.add_argument("--output", required=True, type=Path, help="New JSON file; existing files are not overwritten")
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise FileExistsError()
        source = GoogleSlidesSource(os.environ.get("GOOGLE_SLIDES_ACCESS_TOKEN", ""))
        deck = source.ingest(args.presentation_id)
        serialized = deck_to_json(deck)
        # Exclusive creation also protects against races and symlink overwrites.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(serialized)
    except PresentationSourceError as error:
        print(f"Ingestion failed ({error.code}): {error}", file=sys.stderr)
        return 1
    except OSError:
        print("Cannot write output; supply a new file in an existing writable directory.", file=sys.stderr)
        return 1
    print(f"Wrote normalized snapshot with {len(deck.slides)} slides and {len(deck.issues)} extraction notices.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
