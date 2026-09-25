"""Read-only Google Slides REST adapter with a deterministic pure normalizer."""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from presentation.model import (
    SCHEMA_VERSION, Deck, NormalizationIssue, Provenance, Slide, SlideElement,
    SourceRevision, SpeakerNotes, TableCell, finalize_deck,
)
from presentation.source import PresentationSourceError

MAX_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_GROUP_DEPTH = 32
ELEMENT_KINDS = {
    "shape": "shape", "elementGroup": "group", "table": "table",
    "wordArt": "word_art", "image": "image", "sheetsChart": "chart",
    "video": "video", "line": "line",
}


def _object(value: object) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValueError("Expected an object")
    return value


def _array(value: object) -> list:
    if not isinstance(value, list):
        raise ValueError("Expected an array")
    return value


def _string(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Expected a string")
    return value


def _optional_string(value: object) -> str | None:
    return None if value is None else _string(value)


def _integer(value: object, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError("Invalid nonnegative integer")
    return value


class _Normalizer:
    def __init__(self, document_id: str):
        self.document_id = document_id
        self.object_ids: set[str] = set()
        self.issues = [NormalizationIssue(
            "normalized_subset", "deck",
            "Only direct slide content is normalized. Master/layout inheritance, styling, "
            "geometry, bullets, links, animation, skipped-slide state and visual semantics are omitted.",
        )]

    def provenance(self, page: str | None = None, obj: str | None = None) -> Provenance:
        return Provenance("google_slides", self.document_id, page, obj)

    def object_id(self, value: object) -> str:
        value = _string(value)
        if not value or value in self.object_ids:
            raise ValueError("Missing or duplicate source object ID")
        self.object_ids.add(value)
        return value

    def issue(self, code: str, ref: str, message: str) -> None:
        self.issues.append(NormalizationIssue(code, ref, message))

    def text(self, value: object, ref: str) -> tuple[str, bool]:
        chunks = []
        complete = True
        for item in _array(_object(value).get("textElements", [])):
            item = _object(item)
            kinds = [key for key in ("textRun", "autoText", "paragraphMarker") if key in item]
            if len(kinds) > 1:
                raise ValueError("Multiple text element variants")
            if not kinds:
                complete = False
                continue
            kind = kinds[0]
            content = _object(item[kind])
            if kind != "paragraphMarker":
                chunks.append(_string(content.get("content", "")))
        if not complete:
            self.issue("unsupported_text", ref, "Unrecognized text elements were not interpreted.")
        return "".join(chunks), complete

    def table(self, value: object, ref: str) -> tuple[tuple[TableCell, ...], int, int, bool]:
        table = _object(value)
        rows, columns = _integer(table.get("rows"), 1), _integer(table.get("columns"), 1)
        cells = []
        complete = True
        occupied = set()
        # Bound allocation when validating maliciously large span/dimension values.
        if rows * columns > 100_000:
            raise ValueError("Table exceeds prototype cell limit")
        table_rows = _array(table.get("tableRows", []))
        if len(table_rows) != rows:
            raise ValueError("Incomplete table rows")
        for row_index, row in enumerate(table_rows):
            for cell in _array(_object(row).get("tableCells", [])):
                cell = _object(cell)
                location = _object(cell.get("location", {}))
                r = _integer(location.get("rowIndex", 0))
                c = _integer(location.get("columnIndex", 0))
                rs = _integer(cell.get("rowSpan", 1), 1)
                cs = _integer(cell.get("columnSpan", 1), 1)
                if r != row_index or r + rs > rows or c + cs > columns:
                    raise ValueError("Invalid table cell location/span")
                region = {(i, j) for i in range(r, r + rs) for j in range(c, c + cs)}
                if occupied & region:
                    raise ValueError("Overlapping table cells")
                occupied.update(region)
                text, text_complete = self.text(cell.get("text", {}), ref)
                complete = complete and text_complete
                cells.append(TableCell(r, c, rs, cs, text))
        if len(occupied) != rows * columns:
            raise ValueError("Incomplete table cells")
        return tuple(sorted(cells, key=lambda cell: (cell.row, cell.column))), rows, columns, complete

    def elements(self, values: object, page: str, parent: str, depth: int = 0) -> tuple[SlideElement, ...]:
        if depth > MAX_GROUP_DEPTH:
            raise ValueError("Group nesting exceeds prototype limit")
        result = []
        for position, value in enumerate(_array(values)):
            value = _object(value)
            object_id = self.object_id(value.get("objectId"))
            ref = f"{parent}/element/{position}"
            kinds = [key for key in ELEMENT_KINDS if key in value]
            if len(kinds) > 1:
                raise ValueError("Multiple page element variants")
            key = kinds[0] if kinds else None
            kind = ELEMENT_KINDS.get(key, "unknown")
            content = _object(value[key]) if key else {}
            text, children, cells = "", (), ()
            rows, columns = None, None
            status = "complete"
            if kind == "shape":
                text, complete = self.text(content.get("text", {}), ref)
                status = "complete" if complete else "partial"
            elif kind == "word_art":
                text = _string(content.get("renderedText", ""))
            elif kind == "group":
                children = self.elements(content.get("children", []), page, ref, depth + 1)
                if any(child.extraction_status != "complete" for child in children):
                    status = "partial"
            elif kind == "table":
                cells, rows, columns, complete = self.table(content, ref)
                status = "complete" if complete else "partial"
            else:
                status = "unsupported"
                self.issue("unsupported_element", ref, "Element retained as a marker; visual content is not interpreted.")
            result.append(SlideElement(
                ref, kind, position, self.provenance(page, object_id), text,
                _optional_string(value.get("title")), _optional_string(value.get("description")),
                children, cells, rows, columns, status,
            ))
        return tuple(result)

    def notes(self, slide: Mapping, page_id: str, ref: str) -> SpeakerNotes:
        properties = _object(slide.get("slideProperties", {}))
        if "notesPage" not in properties:
            self.issue("notes_unavailable", ref, "Source response did not include a notes page.")
            return SpeakerNotes("", "unavailable", self.provenance(page_id))
        page = _object(properties["notesPage"])
        notes_page_id = self.object_id(page.get("objectId"))
        notes_properties = _object(page.get("notesProperties", {}))
        notes_id = _optional_string(notes_properties.get("speakerNotesObjectId"))
        provenance = self.provenance(notes_page_id, notes_id)
        found = None
        for element in _array(page.get("pageElements", [])):
            element = _object(element)
            element_id = self.object_id(element.get("objectId"))
            if element_id == notes_id:
                found = element
        if not notes_id:
            self.issue("notes_unavailable", ref, "Speaker-notes object reference is unavailable.")
            return SpeakerNotes("", "unavailable", provenance)
        # Google documents that the referenced shape may not yet exist for empty notes.
        if found is None:
            return SpeakerNotes("", "empty", provenance)
        shape = _object(found.get("shape"))
        text, complete = self.text(shape.get("text", {}), ref)
        status = ("present" if text.strip() else "empty") if complete else "unavailable"
        return SpeakerNotes(text, status, provenance)


def normalize_presentation(payload: Mapping[str, object], *, fetched_at: datetime) -> Deck:
    """Normalize a complete presentations.get response; no network or input mutation."""
    try:
        payload = _object(payload)
        document_id = _string(payload.get("presentationId"))
        if not document_id:
            raise ValueError("Missing document ID")
        normalizer = _Normalizer(document_id)
        slides = []
        for position, value in enumerate(_array(payload.get("slides", []))):
            value = _object(value)
            page_id = normalizer.object_id(value.get("objectId"))
            ref = f"slide/{position}"
            elements = normalizer.elements(value.get("pageElements", []), page_id, ref)
            notes = normalizer.notes(value, page_id, ref + "/notes")
            slides.append(Slide(ref, position, normalizer.provenance(page_id, page_id), elements, notes, ""))
        return finalize_deck(Deck(
            SCHEMA_VERSION, "", _string(payload.get("title", "")), normalizer.provenance(),
            SourceRevision(_optional_string(payload.get("revisionId")), fetched_at),
            tuple(slides), tuple(normalizer.issues),
        ))
    except (ValueError, TypeError, RecursionError):
        raise PresentationSourceError("malformed_source", "Presentation response does not match the supported schema.") from None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "Redirect refused", headers, fp)


class GoogleSlidesSource:
    def __init__(self, access_token: str, *, open_url: Callable | None = None,
                 clock: Callable[[], datetime] | None = None):
        if not access_token or any(ord(char) <= 32 or ord(char) >= 127 for char in access_token):
            raise PresentationSourceError("authentication", "Configure a valid GOOGLE_SLIDES_ACCESS_TOKEN.")
        self._access_token = access_token
        self._open_url = open_url or build_opener(_NoRedirect()).open
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def ingest(self, source_document_id: str) -> Deck:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", source_document_id):
            raise PresentationSourceError("invalid_input", "Supply a presentation ID, not a URL.")
        request = Request(
            f"https://slides.googleapis.com/v1/presentations/{source_document_id}",
            headers={"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"},
        )
        try:
            with self._open_url(request, timeout=30) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise PresentationSourceError("malformed_source", "Presentation exceeds the prototype response limit.")
            payload = json.loads(raw)
        except HTTPError as error:
            code = "authentication" if error.code == 401 else "access" if error.code in (403, 404) else "transport"
            error.close()
            raise PresentationSourceError(code, "Google Slides request failed; check access or retry later.") from None
        except (URLError, OSError, HTTPException):
            raise PresentationSourceError("transport", "Google Slides request did not complete.") from None
        except (ValueError, UnicodeError, RecursionError):
            raise PresentationSourceError("malformed_source", "Google Slides returned invalid JSON.") from None
        deck = normalize_presentation(payload, fetched_at=self._clock())
        if deck.provenance.source_document_id != source_document_id:
            raise PresentationSourceError("malformed_source", "Google Slides returned a different presentation.")
        return deck
