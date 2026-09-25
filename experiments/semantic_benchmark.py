"""Small, sequential model comparison using the unchanged semantic-coverage POC.

Run from the repository root: python3 -m experiments.semantic_benchmark
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from statistics import mean, median
import sys
from time import perf_counter
from typing import Any, Callable

from experiments import semantic_coverage as poc

# Exact IDs returned by the authenticated Token Factory /models on 2026-09-16.
MODELS = (
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
    "nvidia/Nemotron-3_5-Lightning",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/Nemotron-3-Ultra-550b-a55b",
)


def run_benchmark(
    api_key: str,
    models: tuple[str, ...] = MODELS,
    repeats: int = 3,
    request_fn: Callable = poc.request_completion,
    progress: Callable | None = None,
) -> list[dict[str, Any]]:
    """Run all four POC cases, retaining failures and rotating model order each round."""
    if repeats < 1 or not models:
        raise ValueError("At least one repeat and model are required.")
    records = []
    for repeat in range(repeats):
        offset = repeat % len(models)
        for case in poc.CASES:
            for model in models[offset:] + models[:offset]:
                record = {
                    "model": model, "repeat": repeat + 1, "case": case.name,
                    "expected_statuses": list(case.expected_statuses),
                    "matched": False, "usage": {},
                }

                def request(messages, key):
                    response = request_fn(messages, key, model)
                    usage = response.get("usage") or {}
                    # Retain only numeric usage fields, never headers or credentials.
                    record["usage"] = {
                        field: usage.get(field) if type(usage.get(field)) is int
                        and usage[field] >= 0 else None
                        for field in ("prompt_tokens", "completion_tokens", "total_tokens")
                    }
                    choice = response["choices"][0]
                    record["finish_reason"] = choice.get("finish_reason")
                    return choice["message"]["content"]

                started = perf_counter()
                try:
                    result = poc.evaluate_case(case, request, api_key)
                    record["result"] = result
                    record["matched"] = poc.statuses_from(result) == case.expected_statuses
                    record["outcome"] = "pass" if record["matched"] else "mismatch"
                except poc.CoverageResultError:
                    record["outcome"] = "validation_error"
                except poc.TokenFactoryRequestError:
                    record["outcome"] = "request_error"
                record["elapsed_seconds"] = perf_counter() - started
                records.append(record)
                if progress:
                    progress(record)
    return records


def summarize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate all attempts; missing token usage remains unknown, never zero."""
    summaries = []
    for model in dict.fromkeys(row["model"] for row in records):
        rows = [row for row in records if row["model"] == model]
        times = [row["elapsed_seconds"] for row in rows]
        summary = {
            "model": model, "attempts": len(rows),
            "passed": sum(row["matched"] for row in rows),
            "errors": sum(row["outcome"].endswith("error") for row in rows),
            "mean_seconds": mean(times), "median_seconds": median(times),
            "max_seconds": max(times),
        }
        for field in ("prompt_tokens", "completion_tokens"):
            values = [row["usage"].get(field) for row in rows]
            summary[field] = sum(values) if all(v is not None for v in values) else None
        summaries.append(summary)
    return summaries


def comparison_table(records: list[dict[str, Any]]) -> str:
    lines = [
        "| Model | Passed | Errors | Mean s | Median s | Max s | Input tokens | Output tokens |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summarize(records):
        tokens = [str(row[f]) if row[f] is not None else "unknown"
                  for f in ("prompt_tokens", "completion_tokens")]
        lines.append(
            f"| {row['model']} | {row['passed']}/{row['attempts']} | {row['errors']} "
            f"| {row['mean_seconds']:.3f} | {row['median_seconds']:.3f} "
            f"| {row['max_seconds']:.3f} | {tokens[0]} | {tokens[1]} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("experiments/results/semantic-benchmark.json"))
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    api_key = poc.load_api_key(os.environ)
    if not api_key:
        print("NEBIUS_API_KEY is required in the local environment.", file=sys.stderr)
        return 2
    started = datetime.now(timezone.utc).isoformat()
    records = run_benchmark(api_key, repeats=args.repeats, progress=lambda row: print(
        f"Round {row['repeat']} / {row['case'][0]} / {row['model']}: "
        f"{row['outcome']} ({row['elapsed_seconds']:.3f}s)", file=sys.stderr, flush=True))
    report = {
        "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": poc.TOKEN_FACTORY_URL, "models": MODELS, "repeats": args.repeats,
        "settings": {"temperature": 0, "max_tokens": 300,
                     "response_format": {"type": "json_object"}, "timeout_seconds": 30},
        "method": "Sequential, case-interleaved, model order rotated per round; no retries or warmup exclusion.",
        "summary": summarize(records), "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(comparison_table(records))
    return 0 if all(row["matched"] for row in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
