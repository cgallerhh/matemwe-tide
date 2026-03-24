"""
Bundesagentur für Arbeit – offizielle, öffentliche REST-API.
Keine Authentifizierung nötig, kein IP-Blocking, stabiles JSON-Format.

Dokumentation: https://jobsuche.api.bund.dev/
"""
import logging
import time
from typing import Dict, List
from urllib.parse import urlencode

from ..config import MAX_JOBS_PER_QUERY
from .base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"

# BA API needs a specific header to allow unauthenticated access
BA_HEADERS = {
    "X-API-Key": "jobboerse-jobsuche",
}


class ArbeitsagenturScraper(BaseScraper):
    SOURCE_NAME = "Arbeitsagentur"
    POLITE_DELAY = 1.0

    def __init__(self) -> None:
        super().__init__()
        self.session.headers.update(BA_HEADERS)

    def fetch(self, queries: List[str], location: str) -> List[Dict]:
        seen: set = set()
        jobs: List[Dict] = []

        for query in queries:
            try:
                params = {
                    "was": query,
                    "wo": location,
                    "umkreis": "50",
                    "veroeffentlichtseit": "1",   # last 24h
                    "angebotsart": "1",            # regular jobs
                    "size": str(MAX_JOBS_PER_QUERY),
                    "page": "0",
                }
                resp = self.get(BASE_URL, params=params)
                data = resp.json()

                for offer in data.get("stellenangebote") or []:
                    ref = offer.get("refnr", "")
                    job_id = ref or f"{offer.get('titel','')}{offer.get('arbeitgeber','')}"

                    if job_id in seen:
                        continue
                    seen.add(job_id)

                    # Build direct link
                    url = offer.get("externeUrl") or (
                        f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref}"
                        if ref
                        else ""
                    )

                    arbeitsort = offer.get("arbeitsort", {})
                    job_location = ", ".join(
                        filter(None, [arbeitsort.get("ort"), arbeitsort.get("region")])
                    ) or location

                    jobs.append(
                        {
                            "id": job_id,
                            "title": offer.get("titel", "").strip(),
                            "company": offer.get("arbeitgeber", "").strip(),
                            "location": job_location,
                            "url": url,
                            "description": offer.get("stellenbeschreibung", "")[:500].strip()
                            if offer.get("stellenbeschreibung")
                            else "",
                            "posted_date": offer.get("aktuelleVeroeffentlichungsdatum", ""),
                            "source": self.SOURCE_NAME,
                        }
                    )

            except Exception as exc:
                logger.error("Arbeitsagentur query '%s' failed: %s", query, exc)

            time.sleep(self.POLITE_DELAY)

        logger.info("Arbeitsagentur: %d jobs collected", len(jobs))
        return jobs
