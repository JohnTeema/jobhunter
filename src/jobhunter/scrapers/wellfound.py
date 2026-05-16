"""Wellfound (wellfound.com) startup job board scraper."""
from __future__ import annotations
import re, httpx, tenacity
from bs4 import BeautifulSoup
from jobhunter.scrapers.base import BaseScraper
from jobhunter.models import JobListing

BASE = "https://wellfound.com"
UA   = {"User-Agent": "Mozilla/5.0 (compatible; jobhunter/0.1)"}

class WellfoundScraper(BaseScraper):
    source_name = "wellfound"

    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=8),
        stop=tenacity.stop_after_attempt(3),
        reraise=True)
    def _get(self, url: str) -> str:
        with httpx.Client(timeout=15, headers=UA, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
            return r.text

    def fetch(self, pages: int = 1) -> list[JobListing]:
        jobs: list[JobListing] = []
        for p in range(1, pages + 1):
            url = f"https://wellfound.com/jobs?location=remote&page={p}"
            try:
                html = self._get(url)
            except Exception as exc:
                print(f"[wellfound] page {p}: {exc}")
                continue
            soup = BeautifulSoup(html, "lxml")
            for a in soup.select("a[href*='/jobs/']"):
                href  = a.get("href", "")
                if not re.search(r"/jobs/\d", href):
                    continue
                title  = a.get_text(" ", strip=True)
                parent = a.find_parent("div", class_=re.compile(r"job|card", re.I))
                comp_el  = parent.select_one("[class*='company']") if parent else None
                loc_el   = parent.select_one("[class*='location']") if parent else None
                sal_el   = parent.select_one("[class*='salary']") if parent else None
                tags_els = parent.select("[class*='tag'], [class*='pill']") if parent else []

                company   = comp_el.get_text(" ", strip=True) if comp_el else ""
                location  = loc_el.get_text(" ", strip=True) if loc_el else "Remote"
                salary    = sal_el.get_text(" ", strip=True) if sal_el else ""
                tags      = [t.get_text(strip=True) for t in tags_els]

                jobs.append(JobListing(
                    source="wellfound",
                    source_url=BASE + href if href.startswith("/") else href,
                    title=title or "",
                    company=company,
                    location=location,
                    salary_raw=salary,
                    description="",
                    tags=tags,
                    is_remote=True,
                ))
        return jobs
