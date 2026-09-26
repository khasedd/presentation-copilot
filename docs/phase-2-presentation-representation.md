# Phase 2 — Presentation representation foundation

Decision date: September 25, 2026. Status: implemented, verified offline, and live baseline plus owner-approved mutation/reorder checks passed. The Phase 2 exit gate passes, with the unfinished roadmap work preserved. This is a bounded ingestion/representation foundation, not completion of every Phase 2 item. No UI, semantic generation, speech, live session state, or presentation control is implemented here.

## Source decision and suitability

Google Slides is the first supported source, per the owner decision. Its API exposes presentation structure, ordered slides, object references, notes and optional revision metadata. This makes it a practical starting point for later observation/control research; ingestion does **not** prove access to the active slide or establish a live control mechanism. [Google API overview](https://developers.google.com/workspace/slides/api/guides/overview)

PPTX remains a future adapter candidate: it can carry structure and notes but requires separate parsing and revision/live-environment integration. PDF is deferred because export weakens semantic structure, note access, source-object continuity and edit/revision handling. These are scope decisions, not claims that those formats are unusable.

This prototype uses Python's standard library and the official REST API, adding no SDK or license dependency. Google Cloud must have the Slides API enabled; the caller needs authorized access to the chosen deck and an OAuth access token with `presentations.readonly` scope. Token acquisition, consent-screen setup and refresh are external prerequisites. [GET contract](https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/get)

The [official hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules) permit authorized third-party integrations and require substantive runtime Nebius plus NVIDIA open-source-model use. Google is solely the presentation source; the existing Nebius/Nemotron experiment and eventual substantive AI path remain intact. Owner-controlled test content must be used with the required rights, subject to [Google API terms](https://developers.google.com/terms) and [user-data policy](https://developers.google.com/terms/api-services-user-data-policy). This local prototype sends no presentation data to inference. Public OAuth distribution and any later transfer of Google content to inference require their own consent/data-use review; no blanket production-compliance claim is made.

## Adapter boundary

`presentation/source.py` defines `PresentationSource.ingest(source_document_id: str) -> Deck` and categorized `PresentationSourceError` failures. Application logic sees normalized objects, never Google response dictionaries. Provider-specific strings are retained only as provenance values.

`presentation/adapters/google_slides.py` owns authentication, the single read-only HTTP request, Google field interpretation, and `normalize_presentation(payload, *, fetched_at)`. Normalization is pure and leaves its input unchanged. An injected transport and clock allow deterministic offline tests. `presentation/comparison.py` imports only the internal model.

Requests use HTTPS, refuse redirects, and have a 30-second socket timeout and 10 MiB response cap. Groups are limited to 32 nested child levels and tables to 100,000 grid cells. Limits are prototype resource bounds, not Google service limits. There are no retries or token refresh. Authentication, access, transport and malformed-source errors are sanitized; neither provider response bodies nor tokens appear in diagnostics.

## Schema 1.0

Frozen data classes serialize to deterministic JSON. Tuples become ordered JSON arrays and observation timestamps are timezone-aware ISO 8601 strings. `validate_deck` verifies the supported schema, local references/order, provenance consistency and fingerprints. JSON reload/migration is not implemented yet.

| Type | Fields/meaning |
| --- | --- |
| `Deck` | `schema_version`, `snapshot_id`, title, provenance, source revision, ordered slides, extraction issues |
| `Slide` | Snapshot-local ID, zero-based position, provenance, ordered elements, speaker notes, content fingerprint, concepts/status |
| `SlideElement` | Local ID, normalized kind, position, provenance, text, alt title/description, recursive children, table cells/dimensions, extraction status |
| `TableCell` | Row/column coordinates, spans, exact text; source provenance inherited from its table |
| `SpeakerNotes` | Exact text, `present`/`empty`/`unavailable`, notes-page/object provenance |
| `Concept` | Reserved shape: ID, text, supporting local references, derivation method, optional confidence |
| `Provenance` | Provider, source document ID, optional page and object IDs |
| `SourceRevision` | **Only** `revision_id: str \| None` and `fetched_at: datetime` |
| `NormalizationIssue` | Stable code, local reference, explanation |

Concept generation is intentionally deferred. Every imported slide has `concepts=[]` and `concept_status="not_extracted"`; an empty array must not be interpreted as having no required concepts. The validator currently rejects populated concepts. No extraction-confidence score is invented.

IDs such as `slide/0/element/1` are local addresses and must be paired with a snapshot ID. They are neither source IDs nor persistent identities. The SHA-256 snapshot digest includes schema, title, provenance, order and represented content; it excludes fetch time, provider revision tokens, issues and derived concepts. A per-slide fingerprint excludes local/source IDs and slide position, retaining text, notes, element order/hierarchy, table structure, alt text and extraction status. Identical normalized observations can share a snapshot ID. Neither hash is a privacy measure or proof of rendered/semantic equality.

## Normalization and explicit limits

Text runs and available automatic-text content are concatenated in source order without trimming, whitespace folding or Unicode normalization. Paragraph text/newlines are retained; paragraph styling, bullet metadata and inferred reading order are not reconstructed. Groups remain nested. Tables preserve locations, dimensions and merged-cell spans; malformed overlaps, holes or out-of-range cells fail ingestion. Word art retains its rendered text. Empty slides remain present in deck order.

Speaker notes are read only from the designated speaker-notes shape. Decorations on the notes page are excluded. An absent referenced notes shape means empty notes; a missing notes page/reference is reported as unavailable. Unknown text fragments preserve known text and mark extraction incomplete. [Notes semantics](https://developers.google.com/workspace/slides/api/guides/notes)

Images, charts, lines, videos and unknown elements remain explicit unsupported markers with IDs and available alt text. No OCR, image downloads, chart-data requests or visual understanding runs. Styling, geometry, links, animation, skipped-slide state and master/layout-inherited content are omitted and reported by a deck-level issue. Consequently a visual-only edit can escape content fingerprints. `complete` means complete for the documented direct-content subset, not full visual fidelity. Element array order is preserved, not asserted to be human reading order.

## Identity, revision and snapshot comparison

Google object IDs can change during UI edits, including copy/paste and deletion of the original. Retain them as provenance and short-term matching evidence, never as permanent identity. [Google's identity guidance](https://developers.google.com/workspace/slides/api/guides/overview#keeping_track_of_objects_without_using_the_object_id)

Google revision IDs are optional (returned only with edit access), opaque, user-specific and guaranteed valid for 24 hours. Changed tokens need not mean changed content. User/session semantics belong in the adapter/auth layer if later needed; they are absent from `SourceRevision`. The comparator never uses revision tokens to skip content comparison. [Revision contract](https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations)

`compare_snapshots(previous, current)` validates both snapshots and requires the same source. It returns both snapshot IDs, matches, order change, additions/removals, ambiguity groups and limitations:

1. Match retained source slide IDs first; inspect content independently. This establishes correspondence between observations, not proof of identity through arbitrary editing history.
2. Among remaining slides, match only a unique identical content fingerprint on each side, with substantive extracted text or notes. Alt text alone and blank/visual-only slides do not establish a content match.
3. Preserve duplicate candidate groups as ambiguous. Position never breaks ties. Ambiguous candidates are excluded from added/removed lists.
4. Remaining unmatched slides are additions/removals. Changed IDs plus changed content are not guessed to be a match.
5. Compare the relative order of matched slides. An insertion/deletion can shift positions without reordering existing slides. Unmatched and ambiguous slides cannot establish a reorder result.

Each match reports old/new local references and positions, match basis, content/provenance changes and a conservative reuse recommendation:

| Condition | Recommendation |
| --- | --- |
| Represented content or notes changed | `invalidate`: regenerate/review derived concepts |
| Content equal but extraction incomplete | `review_required`: no asserted semantic equivalence |
| Content equal, extraction complete, source references changed | `rebind_required`: rebind evidence references first |
| Equal represented content with unchanged provenance | `eligible`: only for concepts derived from the supported subset; remap snapshot-local references after reorder |
| Ambiguous/unmatched | No reuse recommendation; correspondence is unresolved or absent |

All existing live coverage would require invalidation/re-evaluation across snapshots until a later session-aware policy is implemented. Comparison never authorizes carrying coverage forward or advancing slides. Full persistent identity, fuzzy similarity, neighboring-slide matching and source-history reconciliation remain future work. Omitted visual content, identical duplicates, and an ID reused through arbitrary edits remain limitations.

## Run and verify

From the repository root, with Python 3.10+ (verified here on Python 3.14):

```bash
python3 -m unittest discover -s tests -v
mkdir -p presentation-output
python3 -m experiments.ingest_google_slides PRESENTATION_ID --output presentation-output/deck.json
```

Export `GOOGLE_SLIDES_ACCESS_TOKEN` into the process environment beforehand. The CLI does not automatically load `.env` or obtain credentials. Use secure local environment configuration; never paste a token into a task, command argument or committed file. The `.env.example` value is a placeholder only. Newly created JSON output uses owner-only permissions and exclusive creation; existing files are not overwritten. Treat output as private presentation content and use the ignored `presentation-output/` directory. The CLI prints counts only.

**Offline evidence:** 41 passing tests, including mocked API-to-CLI ingestion, normalization, invalid responses, revisions and reorder/change comparison. The fixture is synthetic and does not prove live access. See [TDD evidence](testing/presentation-representation.tdd.md).

**Initial live-ingestion check — passed September 25, 2026:** ingested an owner-controlled eight-slide fixture at `2026-09-25T19:45:08.593763+00:00`. A second read-only API fetch supplied source data for 189 field assertions covering presentation provenance, ordered slide/object IDs, 14 shape/text objects, notes, a 2×3 table with all six cell coordinates/text values, image provenance/alt text and group hierarchy. Two slides have nonempty notes; the sparse slide retains one text element and empty notes. The opaque revision token was present and matched the second fetch. Replaying that source response reproduces the saved snapshot exactly.

Slides 7 and 8 have identical content fingerprints and distinct source slide IDs. Baseline self-comparison returns eight source-ID matches with no changes or ambiguity; content-only matching of the duplicate pair would be non-unique. No IDs, content or order were changed to exercise fallback matching live. The source contains one group with two empty-text shape children (depth one), so this trial verifies child preservation but does not demonstrate group-inside-group ingestion. Two expected issues were emitted: the global normalized-subset notice and unsupported raster-image semantics.

The normalized snapshot, source response and detailed verification reports are kept only in the ignored `presentation-output/` directory with mode `0600`; no tokens or live deck content are committed. The read-only baseline helper loads only the Slides token from the local `.env` and invokes the documented CLI. That baseline completed before the separate owner-approved mutation pass below.

**Live mutation/reorder check — passed September 25, 2026 (Eastern):** the second snapshot was fetched at `2026-09-26T00:06:58.651772+00:00`. The table slide moved from fourth to second, separate retained-ID slides received visible-text and notes-only edits, a unique slide was added, and the sparse slide was removed. The original title slide was duplicated and its fingerprint verified before replacing the original. The duplicate-content pair retained its source IDs and content. All writes used the current Google revision as a precondition; a fresh read verified the result.

Comparison with the unchanged saved baseline returned seven matches (six by source ID, one by content fingerprint), two content changes, one addition, one removal and `order_changed=true`. The replacement requires rebinding; both edited slides require invalidation. The unchanged image-containing slide still requires review because extraction is incomplete. Neither revision tokens nor a fingerprint establish persistent identity; the provider revision changed as expected. No live coverage state was created or transferred.

The actual source comparison has no ambiguity because duplicate source IDs are retained. A separately labeled in-memory projection withheld only the pair's page-ID hints; it returned one two-by-two ambiguity group and no positional tie-break. Neither live snapshot nor source pair was modified for that simulation. See [mutation evidence](testing/presentation-representation.tdd.md#live-mutationreorder-evidence) for exact results and limitations. The full relevant suite was rerun: 41 passed. The Phase 2 exit gate now passes; semantic extraction, broader edge-case evaluation, other source adapters and full persistent identity remain unfinished. The owner approved the verified Phase 2 foundation for integration through PR #4. Phase 3 has not started.
