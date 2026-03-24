"""
Indeed scraper – versucht zuerst den RSS-Feed, fällt bei 0 Ergebnissen
auf HTML-Scraping zurück.
"""
import hashlib
import logging
import re
import time
from typing import Dict, List
from urllib.parse import urlencode

import feedparser
from bs4 import BeautifulSoup

from ..config import MAX_JOBS_PER_QUERY
from .base import BaseScraper

logger = logging.getLogger(__name__)

RSS_URL  = "https://de.indeed.com/jobs"
HTML_URL = "https://de.indeed.com/jobs"


class IndeedScraper(BaseScraper):
    SOURCE_NAME = "Indeed"

    def fetch(self, queries: List[str], location: str) -> List[Dict]:
        seen: set = set()
        jobs: List[Dict] = []

        for query in queries:
            new = self._rss(query, location, seen)
            if not new:
                new = self._html(query, location, seen)
            jobs.extend(new)
            time.sleep(self.POLITE_DELAY)

        logger.info("Indeed: %d jobs collected", len(jobs))
        return jobs

    # ── RSS ──────────────────────────────────────────────────────────────────

    def _rss(self, query: str, location: str, seen: set) -> List[Dict]:
        try:
            params = {
                "q": query,
                "l": location,
                "radius": "50",
                "sort": "date",
                "format": "rss",
                "lang": "de",
                "limit": str(MAX_JOBS_PER_QUERY),
            }
            url = f"{RSS_URL}?{urlencode(params)}"
            feed = feedparser.parse(url)
            jobs = []
            for entry in feed.entries:
                link = entry.get("link", "")
                job_id = hashlib.md5(link.encode()).hexdigest()
                if job_id in seen:
                    continue
                seen.add(job_id)
                company = ""
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
            return jobs
        except Exception as exc:
            logger.warning("Indeed RSS failed for '%s': %s", query, exc)
            return []

    # ── HTML fallback ─────────────────────────────────────────────────────────

    def _html(self, query: str, location: str, seen: set) -> List[Dict]:
        try:
            params = {
                "q": query,
                "l": location,
                "radius": "50",
                "sort": "date",
                "lang": "de",
            }
            resp = self.get(HTML_URL, params=params)
            soup = BeautifulSoup(resp.text, "lxml")
            jobs = []

            cards = soup.find_all("div", class_=lambda c: c and "job_seen_beacon" in str(c))
            if not cards:
                cards = soup.find_all("a", attrs={"data-jk": True})

            for card in cards[:MAX_JOBS_PER_QUERY]:
                try:
                    title_el = card.find(["h2", "span"], attrs={"title": True}) or card.find("h2")
                    company_el = card.find(attrs={"data-testid": "company-name"}) or \
                                 card.find(class_=lambda c: c and "companyName" in str(c))
                    loc_el = card.find(attrs={"data-testid": "text-location"}) or \
                             card.find(class_=lambda c: c and "companyLocation" in str(c))

                    title = (title_el.get("title") or title_el.get_text(strip=True)) if title_el else ""
                    if not title:
                        continue

                    jk = card.get("data-jk") or ""
                    if not jk:
                        a = card.find("a", attrs={"data-jk": True})
                        jk = a.get("data-jk", "") if a else ""
                    href = f"https://de.indeed.com/viewjob?jk={jk}" if jk else ""
                    job_id = hashlib.md5(href.encode()).hexdigest() if href else \
                             hashlib.md5(title.encode()).hexdigest()

                    if job_id in seen:
                        continue
                    seen.add(job_id)

                    jobs.append(
                        {
                            "id": job_id,
                            "title": title,
                            "company": company_el.get_text(strip=True) if company_el else "",
                            "location": loc_el.get_text(strip=True) if loc_el else location,
                            "url": href,
                            "description": "",
                            "posted_date": "",
                            "source": self.SOURCE_NAME,
                        }
                    )
                except Exception as exc:
                    logger.debug("Indeed card parse error: %s", exc)

            return jobs
        except Exception as exc:
            logger.warning("Indeed HTML failed for '%s': %s", query, exc)
            return []
