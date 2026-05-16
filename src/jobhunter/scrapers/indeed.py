"""
Indeed Nigeria scraper for jobhunter — uses html.parser.

Queries combine self.roles with Nigeria/Remote location filters
passed from config.yaml via BaseScraper.__init__(roles, locations).
"""
from __future__ import annotations
import re
from typing import List
import httpx
from jobhunter.scrapers.base import BaseScraper
from jobhunter.models import JobListing

_UA = {"User-Agent": "Mozilla/5.0 (compatible; jobhunter/0.1)"}


class IndeedScraper(BaseScraper):
    SOURCE = "indeed"

    def fetch(self, pages: int = 1) -> List[JobListing]:
        roles = self.roles or ["product manager remote", "backend engineer remote"]
        locations = self.locations or ["Nigeria"]
        jobs: List[JobListing] = []
        seen_jk: set[str] = set()
        base = "https://ng.indeed.com"

        queries = [f"{role} {loc}" for role in roles for loc in locations]

        for query in queries:
            slug = query.replace(" ", "+")
            for p in range(pages):
                start = p * 10
                url = f"{base}/jobs?q={slug}&remotejob=1&start={start}"
                try:
                    with httpx.Client(timeout=20, headers=_UA, follow_redirects=True) as c:
                        resp = c.get(url); resp.raise_for_status()
                        html_text = resp.text
                except Exception as exc:
                    self.log(f"indeed q={query!r} p={p}: {exc}")
                    continue

                jobs.extend(self._parse(html_text, base, seen_jk))
        return jobs

    def _parse(self, html: str, base: str, seen_jk: set) -> List[JobListing]:
        results: List[JobListing] = []
        # Each job card starts with: <div ... data-jk="...
        rec = re.split(r'(?=<div[^>]+data-jk=")', html)
        for chunk in rec:
            m = re.search(r'data-jk="([a-f0-9]+)"', chunk)
            if not m:
                continue
            jk = m.group(1)
            if jk in seen_jk:
                continue
            seen_jk.add(jk)

            mt = re.search(r'class="[^"]*jobTitle[^"]*">.*?<span[^>]*>([^<]+)<', chunk, re.S)
            title = mt.group(1).strip() if mt else ""

            mc = re.search(r'class="[^"]*company[^"]*"[^>]*>\s*<[^>]+>([^<]+)', chunk, re.S)
            company = mc.group(1).strip() if mc else ""

            ml = re.search(r'class="[^"]*location[^"]*"[^>]*>\s*<[^>]+>([^<]+)', chunk, re.S)
            location = ml.group(1).strip() if ml else ""

            ms = re.search(r'class="[^"]*salary[^"]*"[^>]*>([^<]+)', chunk, re.S)
            salary_raw = ms.group(1).strip() if ms else ""

            mu = re.search(r'href="(/[^"]*tracking[^"]*)"', chunk) or \
                 re.search(r'href="(/jobs[^"]*)"', chunk)
            source_url = f"https://ng.indeed.com{mu.group(1)}" if mu else ""

            results.append(JobListing(
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
        return results
