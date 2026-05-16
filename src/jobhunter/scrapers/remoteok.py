"""
RemoteOK.com scraper — uses public RSS feed (avoids JS-rendered HTML).

Fetch: https://remoteok.com/remote-jobs.rss (returns full XML with all jobs).
Parse: standard xml.etree.ElementTree, map <item> → JobListing.
"""

from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from typing import List
import httpx

from jobhunter.scrapers.base import BaseScraper
from jobhunter.models import JobListing

_RSS_URL = "https://remoteok.com/remote-jobs.rss"
_UA      = {"User-Agent": "Mozilla/5.0 (compatible; jobhunter/0.1)"}


class RemoteOKScraper(BaseScraper):
    SOURCE = "remoteok"

    def fetch(self, pages: int = 1) -> List[JobListing]:
        try:
            with httpx.Client(timeout=20, headers=_UA, follow_redirects=True) as c:
                resp = c.get(_RSS_URL)
                resp.raise_for_status()
                xml_text = resp.text
        except Exception as exc:
            self.log(f"RSS fetch failed: {exc}")
            return []

        return self._parse(xml_text)

    def _parse(self, xml_text: str) -> List[JobListing]:
        jobs: List[JobListing] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            self.log(f"XML parse error: {exc}")
            return []

        channel = root.find("channel")
        if channel is None:
            self.log("no <channel> in RSS")
            return []

        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()

            # description often contains company + salary
            desc = item.findtext("description") or ""

            # Try to extract company from <author> or <dc:creator>
            author_el = item.find("{http://purl.org/dc/elements/1.1/}creator")
            company = (author_el.text if author_el is not None else "") or ""

            # Link / URL
            link_el = item.find("link")
            source_url = (link_el.text if link_el is not None else "").strip()

            # PubDate
            posted = item.findtext("pubDate") or None

            # Salary from description if present
            salary_raw = ""
            salary_m = re.search(r'\$[\d,]+(?:\s*[-–]\s*\$?[\d,]+)?', desc)
            if salary_m:
                salary_raw = salary_m.group()

            # Tags from <category> elements
            tags = [c.text.strip() for c in item.findall("category") if c.text]

            dedup = f"{title}||{company}||{source_url}"
            jobs.append(JobListing(
                source=self.SOURCE,
                source_url=source_url,
                title=title,
                company=company,
                location="Remote",
                salary_raw=salary_raw,
                description=desc[:2000],
                posted=posted,
                tags=tags,
                is_remote=True,
            ))

        self.log(f"RSS parsed {len(jobs)} items")
        return jobs
