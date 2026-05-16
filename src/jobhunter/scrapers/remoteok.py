"""RemoteOK.com scraper."""
from __future__ import annotations
import re, httpx, tenacity
from bs4 import BeautifulSoup
from jobhunter.scrapers.base import BaseScraper
from jobhunter.models import JobListing

BASE = "https://remoteok.com"
UA = {"User-Agent": "Mozilla/5.0 (compatible; jobhunter/0.1)"}

class RemoteOKScraper(BaseScraper):
    source_name = "remoteok"

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1,min=2,max=8),stop=tenacity.stop_after_attempt(3),reraise=True)
    def _get(self, url: str) -> str:
        with httpx.Client(timeout=15, headers=UA) as c:
            r = c.get(url, follow_redirects=True); r.raise_for_status()
            return r.text

    def fetch(self, pages: int = 1) -> list[JobListing]:
        jobs: list[JobListing] = []
        for p in range(1, pages + 1):
            try:
                html = self._get(f"{BASE}/?page={p}")
            except Exception as exc:
                print(f"[remoteok] page {p}: {exc}")
                continue
            soup = BeautifulSoup(html, "lxml")
            rows = soup.find_all("tr", id=re.compile(r"^job-\d+$"))
            for row in rows:
                a = row.find("a", href=re.compile(r"/remote-jobs/"))
                if not a: continue
                h  = row.find("h2") or row.find("h3")
                raw = (h or a).get_text(separator=" ", strip=True)
                comp_el = row.find("a", href=re.compile(r"/companies/"))
                company = comp_el.get_text(strip=True) if comp_el else (raw.split(" at ")[-1].strip() if " at " in raw else "")
                loc_el  = row.find("td", class_=re.compile(r"location", re.I))
                location = loc_el.get_text(strip=True) if loc_el else ""
                sal_el  = row.find("td", class_=re.compile(r"salary", re.I))
                salary  = sal_el.get_text(strip=True) if sal_el else ""
                tag_els = row.find_all("td", class_=re.compile(r"tags", re.I))
                tags    = [t.get_text(strip=True) for t in tag_els]
                href    = a.get("href", "")
                desc_el = row.find("div", class_=re.compile(r"description|markdown", re.I))
                desc    = desc_el.get_text(separator=" ", strip=True) if desc_el else ""
                if raw:
                    jobs.append(JobListing(
                        source="remoteok",
                        source_url=BASE + href if href.startswith("/") else href,
                        title=raw, company=company,
                        location=location, salary_raw=salary,
                        description=desc[:2000], tags=tags,
                        is_remote="remote" in location.lower() or "anywhere" in location.lower(),
                    ))
        return jobs
