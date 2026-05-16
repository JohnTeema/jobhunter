"""Base scraper interface."""
from __future__ import annotations
import abc, typing
from jobhunter.models import JobListing

class BaseScraper(abc.ABC):
    source_name: str = "base"

    @abc.abstractmethod
    def fetch(self, pages: int = 1) -> list[JobListing]:
        raise NotImplementedError
