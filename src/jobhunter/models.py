"""Domain models: JobListing, ScoredJob, DailyShortlist."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

@dataclass
class JobListing:
    source: str
    source_url: str
    title: str
    company: str
    location: str
    salary_raw: str
    description: str
    posted: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    is_remote: bool = False

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "source_url": self.source_url,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "salary_raw": self.salary_raw,
            "description": self.description,
            "posted": self.posted,
            "tags": self.tags,
            "is_remote": self.is_remote,
        }

@dataclass
class ScoredJob:
    listing: JobListing
    score: int           # 0..10
    reasons: list[str]
    personal_note: str

    def to_dict(self) -> dict:
        return {
            **self.listing.to_dict(),
            "score": self.score,
            "reasons": self.reasons,
            "personal_note": self.personal_note,
        }

@dataclass
class DailyShortlist:
    generated_at: str
    criteria: str
    jobs: list[ScoredJob]

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "criteria": self.criteria,
            "jobs": [j.to_dict() for j in self.jobs],
        }
