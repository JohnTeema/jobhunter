"""DuckDuckGo job search — scrapes ONLY job-listing pages (profile/blog pages excluded)."""
from __future__ import annotations
import re, httpx, tenacity
from bs4 import BeautifulSoup
from jobhunter.scrapers.base import BaseScraper
from jobhunter.models import JobListing

BASE = "https://html.duckduckgo.com/html"
UA   = {"User-Agent": "Mozilla/5.0 (compatible; jobhunter/0.1)"}

# Only counts as a real job if the URL contains one of these board paths
_JOB_PATH_RE = re.compile(
    r"/(?:remote-jobs|jobs|remote|career|position|apply|listing|opening)/",
    re.I
)

class DuckDuckGoScraper(BaseScraper):
    source_name = "duckduckgo"

    @tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=8),
        stop=tenacity.stop_after_attempt(3),
        reraise=True)
    def _post(self, url: str, data: dict) -> str:
        with httpx.Client(timeout=15, headers=UA, follow_redirects=True) as c:
            r = c.post(url, data=data); r.raise_for_status(); return r.text

    def fetch(self, pages: int = 1) -> list[JobListing]:
        jobs: list[JobListing] = []
        queries = [
            "site:remoteok.com product manager remote",
            "site:remotive.com backend engineer remote",
            "site:weworkremotely.com python product manager",
            "site:wellfound.com ml engineer remote",
            "site:indiehackers.com jobs",
            "site:startupjobs.com remote",
        ]
        for q in queries[:pages]:
            try:
                html = self._post(BASE, {"q": q})
            except Exception as exc:
                print(f"[duckduckgo] query={q[:40]}: {exc}")
                continue
            soup = BeautifulSoup(html, "lxml")
            for card in soup.select("div.result"):
                a = card.find("a", class_="result__a") or card.find("a")
                if not a:
                    continue
                href   = a.get("href", "")
                title  = a.get_text(" ", strip=True)
                snippet_el = card.find("a", class_="result__snippet") or card.find(class_=re.compile(r"snippet"))
                snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
                if not _JOB_PATH_RE.search(href):
                    continue  # profile / homepage — skip
                jobs.append(JobListing(
                    source="duckduckgo",
                    source_url=href,
                    title=title[:120],
                    company="",
                    location="",
                    salary_raw="",
                    description=snippet[:2000],
                    tags=["duckduckgo"],
                    is_remote=True,
                ))
        return jobs
