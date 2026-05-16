"""
LinkedIn Jobs scraper for jobhunter.
Uses public Search with f_WT=3 (remote) + f_ALR (easy apply).
No Playwright needed — reads data-search-result-card blocks.
"""

from __future__ import annotations
import re
from datetime import datetime
from typing import List
import httpx
from jobhunter.scrapers.base import BaseScraper
from jobhunter.models import JobListing

_UA = {"User-Agent": "Mozilla/5.0 (compatible; jobhunter/0.1)"}

class LinkedinScraper(BaseScraper):
    SOURCE = "linkedin"

    def fetch(self, pages: int = 1) -> List[JobListing]:
        roles = self.roles or ["product manager", "backend engineer"]
        jobs: List[JobListing] = []
        for role in roles:
            slug = role.replace(" ", "%20")
            for p in range(1, pages + 1):
                url = (
                    "https://www.linkedin.com/jobs/search/"
                    f"?keywords={slug}&f_WT=3&f_ALR=true"
                    f"&start={p * 25}"
                )
                try:
                    with httpx.Client(timeout=20, headers=_UA, follow_redirects=True) as c:
                        resp = c.get(url); resp.raise_for_status()
                        html = resp.text
                except Exception as exc:
                    print(f"[linkedin] role={role!r} page={p}: {exc}")
                    continue
                jobs.extend(self._parse(html, url))
        return jobs

    def _parse(self, html: str, url: str) -> List[JobListing]:
        jobs: List[JobListing] = []
        cards = re.split(r'(?=<div[^>]+job-search-card)', html)
        seen: set[str] = set()
        for card in cards:
            m = re.search(r'class="job-search-card__listdate-inner">([^<]+)<', card)
            if not m:
                continue
            title = m.group(1).strip()

            m2 = re.search(r'class="job-search-card__subtitle[^"]*">([^<]+)<', card)
            company = m2.group(1).strip() if m2 else ""

            m3 = re.search(r'class="job-search-card__location[^"]*">([^<]+)<', card)
            location = m3.group(1).strip() if m3 else ""

            m4 = re.search(r'href="(/jobs/view/[^"]+)"', card)
            source_url = f"https://www.linkedin.com{m4.group(1)}" if m4 else url

            m5 = re.search(r'class="job-search-card__salary"[^>]*>([^<]+)<', card)
            salary_raw = m5.group(1).strip() if m5 else ""

            dedup = f"{title}|{company}|{location}"
            if dedup in seen:
                continue
            seen.add(dedup)
            jobs.append(JobListing(
                source=self.SOURCE,
                source_url=source_url,
                title=title,
                company=company,
                location=location,
                salary_raw=salary_raw,
                description="",
                posted=datetime.utcnow().isoformat(),
                tags=[],
                is_remote=False,
            ))
        return jobs
