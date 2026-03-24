"""
StepStone scraper – RSS-Feed via feedparser.
HTML-Scraping wurde ersetzt, da stepstone.de aus Cloud-IPs timeoutet.
"""
import hashlib
import logging
import time
from typing import Dict, List

import feedparser

from ..config import MAX_JOBS_PER_QUERY
from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.stepstone.de"


def _slug(text: str) -> str:
    return (
        text.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("(", "")
        .replace(")", "")
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )


class StepStoneScraper(BaseScraper):
    SOURCE_NAME = "StepStone"
    POLITE_DELAY = 1.5

    def fetch(self, queries: List[str], location: str) -> List[Dict]:
        seen: set = set()
        jobs: List[Dict] = []

        for query in queries:
            try:
                url = (
                    f"{BASE_URL}/stellenangebote"
                    f"--{_slug(query)}"
                    f"--in-{_slug(location)}-.html?rss=1"
                )
                feed = feedparser.parse(url)
                for entry in feed.entries[:MAX_JOBS_PER_QUERY]:
                    link = entry.get("link", "")
                    job_id = (
                        hashlib.md5(link.encode()).hexdigest()
                        if link
                        else hashlib.md5(entry.get("title", "").encode()).hexdigest()
                    )
                    if job_id in seen:
                        continue
                    seen.add(job_id)
                    # dc:creator holds the company name in StepStone's RSS feed
                    company = (
                        entry.get("dc_creator", "")
                        or entry.get("author", "")
                    ).strip()
                    jobs.append({
                        "id": job_id,
                        "title": entry.get("title", "").strip(),
                        "company": company,
                        "location": location,
                        "url": link,
                        "description": entry.get("summary", "")[:500].strip(),
                        "posted_date": entry.get("published", ""),
                        "source": self.SOURCE_NAME,
                    })
            except Exception as exc:
                logger.error("StepStone query '%s' failed: %s", query, exc)
            time.sleep(self.POLITE_DELAY)

        logger.info("StepStone: %d jobs collected", len(jobs))
        return jobs
