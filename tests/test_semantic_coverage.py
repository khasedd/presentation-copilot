"""Unit tests for the semantic-coverage experiment's deterministic behavior."""

import json
import unittest

from experiments.semantic_coverage import (
    CONCEPTS,
    CoverageResultError,
    build_messages,
    parse_coverage_result,
)


class ParseCoverageResultTests(unittest.TestCase):
    def test_accepts_semantically_covered_concept(self) -> None:
        raw_response = json.dumps(
            {
                "concepts": [
                    {"id": 1, "status": "covered"},
                    {"id": 2, "status": "not_covered"},
                    {"id": 3, "status": "not_covered"},
                ],
                "slide_complete": False,
            }
        )

        result = parse_coverage_result(raw_response, CONCEPTS)

        self.assertEqual(result["concepts"][0]["status"], "covered")
        self.assertFalse(result["slide_complete"])

    def test_rejects_keyword_only_statuses_or_extra_scores(self) -> None:
        raw_response = json.dumps(
            {
                "concepts": [
                    {"id": 1, "status": "keyword_match", "confidence": 0.9},
                    {"id": 2, "status": "not_covered"},
                    {"id": 3, "status": "not_covered"},
                ],
                "slide_complete": False,
            }
        )

        with self.assertRaises(CoverageResultError):
            parse_coverage_result(raw_response, CONCEPTS)

    def test_rejects_incorrect_slide_completion(self) -> None:
        raw_response = json.dumps(
            {
                "concepts": [
                    {"id": 1, "status": "covered"},
                    {"id": 2, "status": "not_covered"},
                    {"id": 3, "status": "not_covered"},
                ],
                "slide_complete": True,
            }
        )

        with self.assertRaises(CoverageResultError):
            parse_coverage_result(raw_response, CONCEPTS)


class PromptTests(unittest.TestCase):
    def test_prompt_requires_semantic_not_keyword_coverage(self) -> None:
        messages = build_messages(
            "Transformer Basics",
            CONCEPTS,
            "Attention allows the model to determine which words are relevant.",
        )

        system_prompt = messages[0]["content"]
        self.assertIn("semantic meaning", system_prompt)
        self.assertIn("keyword", system_prompt)
        self.assertIn("not_covered", system_prompt)


if __name__ == "__main__":
    unittest.main()
