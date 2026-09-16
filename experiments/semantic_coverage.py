"""Call Nebius Token Factory to evaluate semantic slide-concept coverage.

This is a deliberately small proof of concept, not production presentation
architecture. It evaluates four fixed transcript cases for one sample slide.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MODEL = "nvidia/nemotron-3-super-120b-a12b"
TOKEN_FACTORY_URL = (
    "https://api.tokenfactory.us-central1.nebius.com/v1/chat/completions"
)
SLIDE_TITLE = "Transformer Basics"
CONCEPTS = (
    {"id": 1, "text": "Attention allows tokens to relate to one another."},
    {"id": 2, "text": "Transformers can process tokens in parallel."},
    {
        "id": 3,
        "text": "Transformers use positional information to preserve token order.",
    },
)

EVALUATION_INSTRUCTIONS = """You evaluate whether a presenter semantically covered
each required slide concept. Mark a concept covered only if the transcript
communicates that concept's semantic meaning. Paraphrases count. A related word or
keyword by itself does not count. Do not infer coverage from general familiarity
with the topic. Use only the transcript as evidence.

Return JSON only, with exactly this shape:
{
  "concepts": [
    {"id": 1, "status": "covered"},
    {"id": 2, "status": "not_covered"}
  ],
  "slide_complete": false
}

Include every supplied concept exactly once. Status must be exactly "covered" or
"not_covered". Do not include explanations, confidence scores, or extra fields.
Set slide_complete to true only when every concept is covered."""


class CoverageResultError(ValueError):
    """Raised when the model response does not match the coverage contract."""


class TokenFactoryRequestError(RuntimeError):
    """Raised when Nebius Token Factory cannot provide a usable completion."""


@dataclass(frozen=True)
class CoverageCase:
    """A fixed qualitative evaluation case for the proof of concept."""

    name: str
    transcript: str
    expected_statuses: tuple[str, str, str]


CASES = (
    CoverageCase(
        name="A — Paraphrased coverage",
        transcript=(
            "Attention allows the model to determine which words are relevant "
            "to other words in the sequence."
        ),
        expected_statuses=("covered", "not_covered", "not_covered"),
    ),
    CoverageCase(
        name="B — Keyword only",
        transcript="This transformer is a powerful model for language tasks.",
        expected_statuses=("not_covered", "not_covered", "not_covered"),
    ),
    CoverageCase(
        name="C — Partial slide coverage",
        transcript=(
            "Attention lets each token weigh which other tokens matter to it. "
            "Unlike recurrent models, a transformer can work on many tokens "
            "simultaneously."
        ),
        expected_statuses=("covered", "covered", "not_covered"),
    ),
    CoverageCase(
        name="D — Complete slide coverage",
        transcript=(
            "Attention lets each token weigh which other tokens matter to it. "
            "Unlike recurrent models, a transformer can work on many tokens "
            "simultaneously. Positional encodings tell the model where tokens "
            "occur, so it can preserve their order."
        ),
        expected_statuses=("covered", "covered", "covered"),
    ),
)


def build_messages(
    slide_title: str, concepts: tuple[dict[str, Any], ...], transcript: str
) -> list[dict[str, str]]:
    """Build the model messages without mixing them with request mechanics."""
    concept_lines = "\n".join(
        f'{concept["id"]}. {concept["text"]}' for concept in concepts
    )
    user_content = (
        f"Slide title: {slide_title}\n\n"
        f"Required concepts:\n{concept_lines}\n\n"
        f"Presenter transcript:\n{transcript}"
    )
    return [
        {"role": "system", "content": EVALUATION_INSTRUCTIONS},
        {"role": "user", "content": user_content},
    ]


def load_api_key(
    environment: Mapping[str, str], env_path: Path = Path(".env")
) -> str | None:
    """Return NEBIUS_API_KEY from the environment or a simple local .env file.

    The file is parsed as data rather than sourced, so configuration cannot run
    shell commands. The key is returned only to the request function and is
    never logged or written.
    """
    if api_key := environment.get("NEBIUS_API_KEY"):
        return api_key

    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", maxsplit=1)
        if name.strip() != "NEBIUS_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return value or None
    return None


def parse_coverage_result(
    raw_result: str, concepts: tuple[dict[str, Any], ...]
) -> dict[str, Any]:
    """Parse and strictly validate the JSON coverage contract from the model."""
    try:
        result = json.loads(raw_result)
    except json.JSONDecodeError as error:
        raise CoverageResultError("Model response was not valid JSON.") from error

    if not isinstance(result, dict) or set(result) != {"concepts", "slide_complete"}:
        raise CoverageResultError("Response must contain only concepts and slide_complete.")

    returned_concepts = result["concepts"]
    if not isinstance(returned_concepts, list) or not isinstance(
        result["slide_complete"], bool
    ):
        raise CoverageResultError("Response has invalid concepts or slide_complete types.")

    expected_ids = [concept["id"] for concept in concepts]
    seen_ids: list[int] = []
    statuses: list[str] = []
    for concept in returned_concepts:
        if not isinstance(concept, dict) or set(concept) != {"id", "status"}:
            raise CoverageResultError("Each concept must contain only id and status.")
        concept_id = concept["id"]
        status = concept["status"]
        if not isinstance(concept_id, int) or status not in {"covered", "not_covered"}:
            raise CoverageResultError("Each concept must have a valid id and status.")
        seen_ids.append(concept_id)
        statuses.append(status)

    if seen_ids != expected_ids:
        raise CoverageResultError("Response concept IDs must match the supplied order exactly.")

    is_complete = all(status == "covered" for status in statuses)
    if result["slide_complete"] != is_complete:
        raise CoverageResultError("slide_complete must equal whether all concepts are covered.")

    return result


def request_completion(
    messages: list[dict[str, str]], api_key: str, model: str = MODEL
) -> dict[str, Any]:
    """Return a usable completion envelope, including provider usage for benchmarking."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
    }
    request = Request(
        TOKEN_FACTORY_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise TokenFactoryRequestError(
            f"Token Factory returned HTTP {error.code}."
        ) from error
    except (URLError, TimeoutError) as error:
        raise TokenFactoryRequestError("Token Factory request failed.") from error
    except json.JSONDecodeError as error:
        raise TokenFactoryRequestError("Token Factory returned invalid JSON.") from error

    try:
        content = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise TokenFactoryRequestError(
            "Token Factory response did not contain a chat completion."
        ) from error
    if not isinstance(content, str):
        raise TokenFactoryRequestError("Token Factory completion content was not text.")
    return response_data


def request_model(messages: list[dict[str, str]], api_key: str) -> str:
    """Preserve the original POC request interface and default model."""
    return request_completion(messages, api_key)["choices"][0]["message"]["content"]


def evaluate_case(
    case: CoverageCase, request_fn: Callable[[list[dict[str, str]], str], str], api_key: str
) -> dict[str, Any]:
    """Evaluate one transcript while keeping model interaction injectable for tests."""
    messages = build_messages(SLIDE_TITLE, CONCEPTS, case.transcript)
    raw_result = request_fn(messages, api_key)
    return parse_coverage_result(raw_result, CONCEPTS)


def statuses_from(result: dict[str, Any]) -> tuple[str, str, str]:
    """Extract the fixed sample slide's statuses for comparison and display."""
    return tuple(concept["status"] for concept in result["concepts"])  # type: ignore[return-value]


def main() -> int:
    """Run all fixed evaluation cases using the locally configured API key."""
    api_key = load_api_key(os.environ)
    if not api_key:
        print("NEBIUS_API_KEY is required in the local environment.", file=sys.stderr)
        return 2

    print(f"Model: {MODEL}")
    print(f"Slide: {SLIDE_TITLE}")
    all_matched = True
    for case in CASES:
        try:
            result = evaluate_case(case, request_model, api_key)
        except (CoverageResultError, TokenFactoryRequestError) as error:
            print(f"\n{case.name}\nERROR: {error}")
            all_matched = False
            continue

        actual_statuses = statuses_from(result)
        matched = actual_statuses == case.expected_statuses
        all_matched = all_matched and matched
        print(f"\n{case.name}")
        print(f"Transcript: {case.transcript}")
        print("Returned:")
        print(json.dumps(result, indent=2))
        print(f"Expected statuses: {list(case.expected_statuses)}")
        print(f"Matched expected behavior: {matched}")

    return 0 if all_matched else 1


if __name__ == "__main__":
    raise SystemExit(main())
