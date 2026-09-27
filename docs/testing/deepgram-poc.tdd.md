# Deepgram Phase 3 POC — TDD evidence

Recorded September 27, 2026 on `codex/phase-3-deepgram-poc`. Journeys were derived from the bounded Phase 3 acceptance test; no separate plan file was used.

## User journeys

1. As downstream transcript logic, receive Deepgram callbacks through unchanged `TranscriptEvent` 1.0 semantics, including revisions, finality, shorter finals, timestamps, failures, and reconnect boundaries.
2. As the experiment operator, stream one explicitly selected microphone without persisting raw audio, transcript/reference text, or credentials, and retain only owner-readable aggregate evidence.
3. As a reviewer, reproduce deterministic behavior without network/audio and distinguish it from the still-required physical spoken trials.

## RED/GREEN task report

| Behavior | RED checkpoint and observed failure | GREEN checkpoint and validation | Guarantee |
| --- | --- | --- | --- |
| Provider normalization | `508e8b2`: adapter tests failed because the module/behavior did not exist | `d4749d3`; focused 10-test adapter suite passed | Adapter owns IDs/counters and safely maps partial/final, shorter-final, no-op, malformed, close, failure, and reconnect behavior |
| Live harness configuration/privacy/measurement | `8e4efd1`: harness tests failed because the experiment did not exist | `1931040`; focused harness tests and authenticated preflights passed | Exact request options, capture conversion, aggregate-only report, WER/term recall, and bounded trial shape are executable |
| Empty provider result metrics | `126ec76`: an empty result incorrectly incremented endpoint/latency evidence | `d5f8003`; focused regression and full suite passed | Empty/no-op callbacks cannot inflate measured speech latency or endpoints |
| Failed evidence reservation | `58c73ba`: simulated trial failure left an empty reserved JSON file | `0207b71`; focused regression and full suite passed | Any exception closes the descriptor and removes partial/empty aggregate evidence so a retry is safe |
| Monotonic stream closure | `c571480`: a provider-timed final followed by a fast close raised `invalid_transition` because close time regressed | `188cc3f`; focused transport test and full suite passed | Close/failure observation offsets never regress below the last accepted provider-aligned event |

All checkpoint commits are reachable from the current branch head and belong to this POC sequence.

## Test specification

| What is guaranteed | Test/evidence | Type | Result |
| --- | --- | --- | --- |
| Initial, revised, final, shorter-final, failure, reconnect, malformed and old-stream callbacks obey schema 1.0 | `tests/test_deepgram_adapter.py` (10 tests) | Unit/integration with accumulator | PASS |
| Nova-3 request has 16 kHz mono `linear16`, 50 ms chunks, `endpointing=500`, interim/VAD/punctuation/smart formatting and `mip_opt_out=true`, without diarization | `test_listen_url_has_required_privacy_audio_and_latency_settings` | Unit | PASS |
| `.env` is parsed as data and never executed; environment wins | `test_key_loader_prefers_environment_and_never_executes_env_file` | Security unit | PASS |
| PipeWire-Pulse capture requests in-memory conversion and no file format | `test_capture_requests_pipewire_conversion_to_transmitted_format` | Unit plus host capture preflight | PASS |
| Empty results do not create latency/endpoint samples | `test_empty_result_does_not_create_latency_or_endpoint_samples` | Regression | PASS |
| Failed runs leave no output; successful JSON is owner-only and cannot escape the ignored output root | `DeepgramLiveCliTests` | Security/integration | PASS |
| Trial C uses two fresh streams and never reports cross-stream WER | `test_trial_orchestration_uses_one_stream_or_two_fresh_streams` and `test_combined_report_never_scores_across_reconnected_streams` | Orchestration | PASS |
| Metadata, speech boundary, result, normal close and intentional interruption traverse the transport path | `test_stream_transport_consumes_metadata_result_and_interrupts_safely` | Mock transport integration | PASS |
| Real API accepts the exact request and real reconnect creates distinct streams | ignored `preflight-handshake.json` and `preflight-reconnect.json`, inspected only for aggregate fields | Live transport preflight | PASS |
| Near/far spoken accuracy, real partial churn, endpoint latency and spoken reconnect behavior meet fixed thresholds | Trials A, B and C | Physical live E2E | PENDING PRESENTER |

## Coverage and known gaps

`python3 -m trace --count --missing --summary --module unittest discover -s tests` reports **88.6%** line coverage for `transcription.adapters.deepgram` and **80.8%** for `experiments.deepgram_live`. `python3 -m unittest discover -s tests -v` passes **120/120 tests**.

The deterministic suite mocks transport only where needed; it does not claim microphone acoustics or provider quality. A real in-memory capture, authenticated 1.8-second handshake, 5.6-second disconnect/reconnect preflight, and 1.6-second post-fix handshake passed. The 9.0 total billable preflight seconds have an estimated cost of $0.000720. Those silence/noise checks are not substitutes for the fixed 90-second near-field trial, 90-second presentation-distance/noise trial, and 60-second spoken reconnect trial. Exact account balance, promotional-credit origin, expiry, and an independently retrievable `mip_opt_out` request record remain unavailable to the configured key; no billing action was taken.
