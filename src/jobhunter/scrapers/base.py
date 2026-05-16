"""Base scraper interface."""
from __future__ import annotations
import abc, typing
from jobhunter.models import JobListing

class BaseScraper(abc.ABC):
    source_name: str = "base"

    def __init__(self, roles: list[str] | None = None, locations: list[str] | None = None):
        self.roles = roles or []
        self.locations = locations or []

    @abc.abstractmethod
    def fetch(self, pages: int = 1) -> list[JobListing]:
        raise NotImplementedError
