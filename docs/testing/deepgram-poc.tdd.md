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
| Trailing-window final correction | `a42e790`: a live-shaped final ending just before its longer interim was rejected even though all timed words were inside the final span | `936a41e`; focused regression and full suite passed | A shorter final with no timed remainder is accepted as one normal revision when no word evidence requires a new segment |
| Mid-word shorter final | `ea9ad8e`: a live-shaped final boundary crossed the first tentative remainder word and caused a blocking incompatibility | `4f73fc4`; focused regression and full suite passed | The provisional remainder starts at the authoritative final boundary while preserving the provider word's end and text |
| Provider word metadata variance | `366e1ac`: overlapping word timings, an empty punctuated form, and one-millisecond boundary drift were rejected as malformed | `f82e1df`; focused regressions and full suite passed | Result ranges remain authoritative; ordinary word overlap is accepted, raw words backfill empty punctuated forms, and one-millisecond rounding drift is clipped |
| Optional result metadata and empty alternatives | `a55b615` and `2355ad6`: optional invalid/out-of-range word hints and a documented empty `alternatives` callback aborted an otherwise usable stream | `e8ff153`; 17 focused adapter tests and the 127-test suite passed | Empty alternatives are a no-op; optional word hints are clipped or skipped; malformed required fields retain atomic rejection with a content-free reason code |

All checkpoint commits are reachable from the current branch head and belong to this POC sequence.

## Test specification

| What is guaranteed | Test/evidence | Type | Result |
| --- | --- | --- | --- |
| Initial, revised, final, shorter-final, failure, reconnect, malformed, empty-alternative, word-metadata variance and old-stream callbacks obey schema 1.0 | `tests/test_deepgram_adapter.py` (17 tests) | Unit/integration with accumulator | PASS |
| Nova-3 request has 16 kHz mono `linear16`, 50 ms chunks, `endpointing=500`, interim/VAD/punctuation/smart formatting and `mip_opt_out=true`, without diarization | `test_listen_url_has_required_privacy_audio_and_latency_settings` | Unit | PASS |
| `.env` is parsed as data and never executed; environment wins | `test_key_loader_prefers_environment_and_never_executes_env_file` | Security unit | PASS |
| PipeWire-Pulse capture requests in-memory conversion and no file format | `test_capture_requests_pipewire_conversion_to_transmitted_format` | Unit plus host capture preflight | PASS |
| Empty results do not create latency/endpoint samples | `test_empty_result_does_not_create_latency_or_endpoint_samples` | Regression | PASS |
| Failed runs leave no output; successful JSON is owner-only and cannot escape the ignored output root | `DeepgramLiveCliTests` | Security/integration | PASS |
| Trial C uses two fresh streams and never reports cross-stream WER | `test_trial_orchestration_uses_one_stream_or_two_fresh_streams` and `test_combined_report_never_scores_across_reconnected_streams` | Orchestration | PASS |
| Metadata, speech boundary, result, normal close and intentional interruption traverse the transport path | `test_stream_transport_consumes_metadata_result_and_interrupts_safely` | Mock transport integration | PASS |
| Real API accepts the exact request and real reconnect creates distinct streams | ignored `preflight-handshake.json` and `preflight-reconnect.json`, inspected only for aggregate fields | Live transport preflight | PASS |
| Near/far spoken accuracy, real partial churn, endpoint latency and spoken reconnect behavior meet fixed thresholds | Trials A, B and C | Physical live E2E | PENDING VALID TRIALS |

## Coverage and known gaps

`python3 -m trace --count --missing --summary --module unittest discover -s tests` reports **89.1%** line coverage for `transcription.adapters.deepgram` and **80.8%** for `experiments.deepgram_live`. `python3 -m unittest discover -s tests -v` passes **127/127 tests**.

The deterministic suite mocks transport only where needed; it does not claim microphone acoustics or provider quality. A real in-memory capture, authenticated 1.8-second handshake, 5.6-second disconnect/reconnect preflight, 1.6-second post-fix handshake, and 14.55-second content-free smoke run passed. Completed aggregate reports therefore account for 23.55 billable seconds, with an estimated cost of $0.001884; provider usage for failed streams is unavailable to this key and is not included in that exact subtotal.

Four attempted Trial A reads exercised real speech but terminated before a valid scored report. The first three exposed the trailing-window final, mid-word remainder, and provider word-metadata cases. The fourth ran about 77 seconds before the old generic `invalid_provider_message` error; that code cannot distinguish an empty-alternatives callback from optional word-hint variance. Both harmless shapes are now covered, while malformed required fields have content-free reason codes. Failure cleanup removed each reserved aggregate file, so none is presented as WER, recall, latency, or endpoint evidence. A fresh Trial A is still required after these fixes, followed by B and C. Exact account balance, promotional-credit origin, expiry, and an independently retrievable `mip_opt_out` request record remain unavailable to the configured key; no billing action was taken.
