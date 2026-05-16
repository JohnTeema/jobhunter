"""Naukri.com job search (India-focused, useful for engineer roles in Nigeria too)."""
from __future__ import annotations
import re, httpx, tenacity
from bs4 import BeautifulSoup
from jobhunter.scrapers.base import BaseScraper
from jobhunter.models import JobListing

BASE = "https://www.naukri.com"
UA   = {"User-Agent": "Mozilla/5.0 (compatible; jobhunter/0.1)"}

class NaukriScraper(BaseScraper):
    source_name = "naukri"

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1,min=2,max=8),stop=tenacity.stop_after_attempt(3),reraise=True)
    def _get(self, url: str) -> str:
        with httpx.Client(timeout=15, headers=UA, follow_redirects=True) as c:
            r = c.get(url); r.raise_for_status(); return r.text

    def fetch(self, pages: int = 1) -> list[JobListing]:
        jobs: list[JobListing] = []
        roles    = ["product+manager", "backend+engineer"]
        locs     = ["nigeria", "remote"]
        for p in range(pages):
            for role in roles[:2]:
                for loc in locs[:2]:
                    url = f"{BASE}/{role}-jobs-in-{loc}-?pageNo={p+1}"
                    try:
                        html = self._get(url)
                    except Exception as exc:
                        print(f"[naukri] page {p+1} role={role}: {exc}"); continue
                    soup = BeautifulSoup(html, "lxml")
                    for card in soup.find_all("article", class_=re.compile(r"jobTuple")):
                        a = card.find("a", class_=re.compile(r"title"))
                        if not a: continue
                        href   = a.get("href", "")
                        title  = a.get_text(strip=True)
                        sal_el = card.find(class_=re.compile(r"salary"))
                        loc_el = card.find(class_=re.compile(r"location"))
                        comp_el = card.find(class_=re.compile(r"compName"))
                        tags   = [t.get_text(strip=True) for t in card.select(".tags")]
                        jobs.append(JobListing(
                            source="naukri",
                            source_url=href,
                            title=title or "",
                            company=comp_el.get_text(strip=True) if comp_el else "",
                            location=loc_el.get_text(strip=True) if loc_el else loc,
                            salary_raw=sal_el.get_text(strip=True) if sal_el else "",
                            description="",
                            tags=tags,
                            is_remote=True,
                        ))
        return jobs
