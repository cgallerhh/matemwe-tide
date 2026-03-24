"""
Indeed scraper – uses the public RSS feed (no authentication required).
Filter: jobs posted in the last 24 hours (fromage=1).
"""
import hashlib
import logging
import time
from typing import Dict, List
from urllib.parse import urlencode

import feedparser

from ..config import MAX_JOBS_PER_QUERY
from .base import BaseScraper

logger = logging.getLogger(__name__)

RSS_URL = "https://de.indeed.com/jobs"


class IndeedScraper(BaseScraper):
    SOURCE_NAME = "Indeed"

    def fetch(self, queries: List[str], location: str) -> List[Dict]:
        seen: set = set()
        jobs: List[Dict] = []

        for query in queries:
            try:
                params = {
                    "q": query,
                    "l": location,
                    "radius": "50",
                    "sort": "date",
                    "fromage": "1",   # posted in the last 24h
                    "format": "rss",
                    "lang": "de",
                    "limit": str(MAX_JOBS_PER_QUERY),
                }
                url = f"{RSS_URL}?{urlencode(params)}"
                feed = feedparser.parse(url)

                for entry in feed.entries:
                    link = entry.get("link", "")
                    job_id = hashlib.md5(link.encode()).hexdigest()
                    if job_id in seen:
                        continue
                    seen.add(job_id)

                    company = ""
                    # feedparser stores Indeed's company in various places
                    if hasattr(entry, "source"):
                        company = getattr(entry.source, "title", "")
                    if not company:
                        company = entry.get("indeed_company", "")

                    jobs.append(
                        {
                            "id": job_id,
                            "title": entry.get("title", "").strip(),
                            "company": company.strip(),
                            "location": entry.get(
                                "indeed_formattedlocation", location
                            ).strip(),
                            "url": link,
                            "description": entry.get("summary", "")[:500].strip(),
                            "posted_date": entry.get("published", ""),
                            "source": self.SOURCE_NAME,
                        }
                    )
            except Exception as exc:
                logger.error("Indeed query '%s' failed: %s", query, exc)

            time.sleep(self.POLITE_DELAY)

        logger.info("Indeed: %d jobs collected", len(jobs))
        return jobs
