"""
Bundesagentur für Arbeit – RSS-Feed der öffentlichen Jobbörse.

Der OAuth-REST-Endpoint (rest.arbeitsagentur.de/oauth/token) ist von
GitHub Actions IPs per WAF gesperrt (403). Stattdessen wird der öffentliche
RSS-Feed der Jobbörse genutzt, der auf einer anderen Infrastruktur läuft.

Feed-URL: https://jobboerse.arbeitsagentur.de/vamJB/sucheAusgabe.html
          ?aa=1&m=1&beruf={query}&arbeitsort={location}&umkreis=50
          &veroeffentlichtseit=3&format=rss
"""
import hashlib
import logging
import time
from typing import Dict, List
from urllib.parse import quote_plus

import feedparser

from ..config import MAX_JOBS_PER_QUERY
from .base import BaseScraper

logger = logging.getLogger(__name__)

RSS_BASE = "https://jobboerse.arbeitsagentur.de/vamJB/sucheAusgabe.html"


class ArbeitsagenturScraper(BaseScraper):
    SOURCE_NAME = "Arbeitsagentur"
    POLITE_DELAY = 1.0

    def fetch(self, queries: List[str], location: str) -> List[Dict]:
        seen: set = set()
        jobs: List[Dict] = []

        for query in queries:
            try:
                url = (
                    f"{RSS_BASE}"
                    f"?aa=1&m=1"
                    f"&beruf={quote_plus(query)}"
                    f"&arbeitsort={quote_plus(location)}"
                    f"&umkreis=50"
                    f"&veroeffentlichtseit=3"
                    f"&format=rss"
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
                logger.error("Arbeitsagentur query '%s' failed: %s", query, exc)
            time.sleep(self.POLITE_DELAY)

        logger.info("Arbeitsagentur: %d jobs collected", len(jobs))
        return jobs
