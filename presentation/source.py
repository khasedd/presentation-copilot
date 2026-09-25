"""The application-facing ingestion boundary; Google JSON stays in its adapter."""
from typing import Protocol

from presentation.model import Deck


class PresentationSourceError(RuntimeError):
    """Safe public error; never include a token or raw provider response."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class PresentationSource(Protocol):
    def ingest(self, source_document_id: str) -> Deck:
        """Return a validated snapshot or raise PresentationSourceError."""
        ...
