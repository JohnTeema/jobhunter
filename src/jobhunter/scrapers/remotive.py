"""Remotive.com scraper (uses their public API)."""
from __future__ import annotations
import json, httpx, tenacity
from jobhunter.scrapers.base import BaseScraper
from jobhunter.models import JobListing

BASE = "https://remotive.com"
UA   = {"User-Agent": "Mozilla/5.0 (compatible; jobhunter/0.1)"}

class RemotiveScraper(BaseScraper):
    source_name = "remotive"

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1,min=2,max=8),stop=tenacity.stop_after_attempt(3),reraise=True)
    def _get(self, url: str) -> str:
        with httpx.Client(timeout=15, headers=UA) as c:
            r = c.get(url, follow_redirects=True); r.raise_for_status()
            return r.text

    def fetch(self, pages: int = 1) -> list[JobListing]:
        jobs: list[JobListing] = []
        for p in range(1, pages + 1):
            url = f"{BASE}/api/remote-jobs?limit=100&page={p}"
            try:
                with httpx.Client(timeout=15, headers=UA) as c:
                    r = c.get(url); r.raise_for_status()
                    data = r.json()
            except Exception as exc:
                print(f"[remotive] page {p}: {exc}")
                continue
            for item in data.get("jobs", []):
                jobs.append(JobListing(
                    source="remotive",
                    source_url=f"{BASE}/jobs/{item.get('id','')}",
                    title=item.get("title",""),
                    company=item.get("company_name",""),
                    location=item.get("candidate_required_location",""),
                    salary_raw=item.get("salary",""),
                    description=item.get("description","")[:2000],
                    tags=item.get("tags",[]),
                    is_remote=True,
                ))
        return jobs
