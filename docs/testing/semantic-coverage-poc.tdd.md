# Semantic-coverage proof-of-concept test evidence

## Source and user journey

No external plan file was used. The task-derived journey is: **as a presenter, I want a slide concept counted only when my transcript communicates its meaning, so that a keyword mention does not falsely advance the presentation.**

## RED → GREEN evidence

The initial contract test was added in commit `b9f83c2` and run with:

```text
python3 -m unittest tests/test_semantic_coverage.py
```

It failed as intended with `ModuleNotFoundError: No module named 'experiments'`. The implementation was then added in commit `30784ab`; after a prompt wording assertion exposed the missing literal “semantic meaning,” the test suite was rerun successfully:

```text
python3 -m unittest discover -s tests -v
python3 -m py_compile experiments/semantic_coverage.py
```

Final result: 5 tests passed. The live integration command `python3 experiments/semantic_coverage.py` then returned the expected outcomes for cases A–D from Token Factory.

| # | Guarantee | Test or command | Type | Result |
| --- | --- | --- | --- | --- |
| 1 | A valid binary coverage result parses. | `ParseCoverageResultTests.test_accepts_semantically_covered_concept` | Unit | PASS |
| 2 | Extra scores and statuses outside the two-value contract are rejected. | `test_rejects_keyword_only_statuses_or_extra_scores` | Unit | PASS |
| 3 | `slide_complete` cannot contradict concept statuses. | `test_rejects_incorrect_slide_completion` | Unit | PASS |
| 4 | The model prompt explicitly requires semantic—not keyword—coverage. | `PromptTests.test_prompt_requires_semantic_not_keyword_coverage` | Unit | PASS |
| 5 | A local `.env` key is read as data, not executed as shell. | `ConfigurationTests.test_loads_key_from_existing_env_file_without_executing_it` | Unit | PASS |
| 6 | The selected model handles the four fixed semantic cases. | `python3 experiments/semantic_coverage.py` | Live integration | PASS |

## Coverage and known gaps

`python3 -m coverage run -m unittest discover -s tests` could not run because the environment has no `coverage` module. No dependency was installed for this isolated proof of concept. The unit tests cover the deterministic prompt/result/configuration contract, while live testing covers successful request/response behavior only. HTTP error branches, timeout behavior, malformed provider responses, and broad semantic accuracy need future tests and representative evaluation data.
