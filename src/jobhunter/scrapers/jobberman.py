

"""Jobberman Nigeria scraper for jobhunter — uses html.parser."""
from __future__ import annotations
import re
from typing import List

import bs4
import httpx

from jobhunter.scrapers.base import BaseScraper
from jobhunter.models import JobListing

base_url_jb = "https://www.jobberman.com/jobs"
UA = {"User-Agent": "Mozilla/5.0 (compatible; jobhunter/0.1)"}

class JobbermanScraper(BaseScraper):
    SOURCE = "jobberman"

    def fetch(self, pages: int = 1) -> List[JobListing]:
        roles = self.roles or ["product manager", "backend engineer"]
        jobs: List[JobListing] = []
        seen: set[str] = set()
        base = "https://www.jobberman.com"

        for role in roles:
            slug = role.replace(" ", "+")
            for p in range(pages):
                url = f"{base_url_jb}?q={slug}&page={p+1}"
                try:
                    with httpx.Client(timeout=20, headers=UA, follow_redirects=True) as c:
                        html = c.get(url); html.raise_for_status()
                except Exception as exc:
                    print("  [jobberman] ", f"jobberman role={role} page={p}: {exc}")
                    continue

                soup = bs4.BeautifulSoup(html.text, "html.parser")
                for card in soup.select(".job-card-listing, .card-content, [data-automation='job-listing']"):
                    title_el  = card.select_one("h3, .job-title, [data-automation='job-title']")
                    title     = title_el.get_text(strip=True) if title_el else ""
                    company_el = card.select_one(".company-name, [data-automation='job-company-name']")
                    company   = company_el.get_text(strip=True) if company_el else ""
                    loc_el    = card.select_one(".job-location, .location, [data-automation='job-location']")
                    location  = loc_el.get_text(strip=True)  if loc_el  else ""
                    salary_el = card.select_one(".salary, [data-automation='job-salary']")
                    salary_raw = salary_el.get_text(strip=True) if salary_el else ""
                    link_el   = card.select_one("a[href]")
                    if link_el:
                        href = link_el.get("href", "") or ""
                        source_url = href if href.startswith("http") else (base + href if href.startswith("/") else href)
                    else:
                        source_url = base

                    dedup = f"{title}||{company}||{location}"
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
                        posted=None,
                        tags=[],
                        is_remote=False,
                    ))
        return jobs
