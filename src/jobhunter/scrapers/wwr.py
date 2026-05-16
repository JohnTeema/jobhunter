"""WeWorkRemotely.com scraper."""
from __future__ import annotations
import re, httpx, tenacity
from bs4 import BeautifulSoup
from jobhunter.scrapers.base import BaseScraper
from jobhunter.models import JobListing

BASE = "https://weworkremotely.com"
UA   = {"User-Agent": "Mozilla/5.0 (compatible; jobhunter/0.1)"}

class WWRScraper(BaseScraper):
    source_name = "wwr"

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
        for p in range(pages):
            url = f"{BASE}/categories/engineering/jobs"
            try:
                html = self._get(url)
            except Exception as exc:
                print(f"[wwr] page {p+1}: {exc}")
                continue
            soup = BeautifulSoup(html, "lxml")
            for li in soup.find_all("li", class_=re.compile(r"feature|job")):
                a = li.find("a", href=re.compile(r"/listings/"))
                if not a:
                    continue
                href  = a.get("href", "")
                title = a.get_text(" ", strip=True)
                spans = a.find_all("span")
                comp  = spans[0].get_text(strip=True) if spans else ""
                tags  = [s.get_text(strip=True) for s in spans[1:]]
                jobs.append(JobListing(
                    source="wwr",
                    source_url=BASE + href if href.startswith("/") else href,
                    title=title or "",
                    company=comp,
                    location="Remote",
                    salary_raw="",
                    description="",
                    tags=tags,
                    is_remote=True,
                ))
        return jobs
