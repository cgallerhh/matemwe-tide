"""
Indeed scraper – RSS-Feed via feedparser.

feedparser.parse(url) nutzt intern urllib ohne Browser-Headers – Indeed blockt
das lautlos (0 Ergebnisse). Fix: zuerst mit der Browser-Session fetchen,
dann den Response-Text an feedparser übergeben.
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
            jobs.extend(self._rss(query, location, seen))
            time.sleep(self.POLITE_DELAY)

        logger.info("Indeed: %d jobs collected", len(jobs))
        return jobs

    def _rss(self, query: str, location: str, seen: set) -> List[Dict]:
        try:
            params = {
                "q": query,
                "l": location,
                "sort": "date",
                "fromage": "3",
                "format": "rss",
            }
            url = f"{RSS_URL}?{urlencode(params)}"
            # Fetch with browser session so Indeed doesn't block the request
            resp = self.session.get(
                url,
                headers={"Accept": "application/rss+xml, application/xml, */*"},
                timeout=15,
            )
            feed = feedparser.parse(resp.text)
            if feed.bozo and feed.entries == []:
                logger.warning("Indeed RSS parse issue for '%s': %s", query, feed.bozo_exception)
                return []
            jobs = []
            for entry in feed.entries[:MAX_JOBS_PER_QUERY]:
                link = entry.get("link", "")
                job_id = hashlib.md5(link.encode()).hexdigest()
                if job_id in seen:
                    continue
                seen.add(job_id)
                company = entry.get("indeed_company", "")
                if not company and hasattr(entry, "source"):
                    company = getattr(entry.source, "title", "")
                jobs.append({
                    "id": job_id,
                    "title": entry.get("title", "").strip(),
                    "company": company.strip(),
                    "location": entry.get("indeed_formattedlocation", location).strip(),
                    "url": link,
                    "description": entry.get("summary", "")[:500].strip(),
                    "posted_date": entry.get("published", ""),
                    "source": self.SOURCE_NAME,
                })
            return jobs
        except Exception as exc:
            logger.warning("Indeed RSS failed for '%s': %s", query, exc)
            return []
