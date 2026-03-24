"""
Bundesagentur für Arbeit – offizielle REST-API.
OAuth2 Client Credentials Flow (kein Secret erforderlich).

Der Token-Endpoint prüft Origin/Referer via WAF. Wir senden dieselben
Headers wie der Browser auf www.arbeitsagentur.de/jobsuche/.

Dokumentation: https://jobsuche.api.bund.dev/
"""
import logging
import time
from typing import Dict, List, Optional

import requests

from ..config import MAX_JOBS_PER_QUERY
from .base import BaseScraper

logger = logging.getLogger(__name__)

TOKEN_URL = "https://rest.arbeitsagentur.de/oauth/token"
BASE_URL  = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
CLIENT_ID = "jobboerse-jobsuche"


class ArbeitsagenturScraper(BaseScraper):
    SOURCE_NAME = "Arbeitsagentur"
    POLITE_DELAY = 1.0

    def __init__(self) -> None:
        super().__init__()
        self._token: Optional[str] = None

    def _get_token(self) -> str:
        # Mimic the headers the Arbeitsagentur web frontend sends when it
        # fetches the OAuth token – the WAF checks Origin/Referer.
        resp = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials", "client_id": CLIENT_ID},
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Origin": "https://www.arbeitsagentur.de",
                "Referer": "https://www.arbeitsagentur.de/",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            },
            timeout=15,
        )
        resp.raise_for_status()
        token = resp.json().get("access_token", "")
        logger.info("Arbeitsagentur: OAuth token obtained (%d chars)", len(token))
        return token

    def _search(self, params: dict) -> dict:
        resp = self.session.get(
            BASE_URL,
            params=params,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            },
            timeout=20,
        )
        if not resp.ok:
            logger.error(
                "Arbeitsagentur API %d – body: %s", resp.status_code, resp.text[:300]
            )
            resp.raise_for_status()
        return resp.json()

    def fetch(self, queries: List[str], location: str) -> List[Dict]:
        seen: set = set()
        jobs: List[Dict] = []

        try:
            self._token = self._get_token()
        except Exception as exc:
            logger.error("Arbeitsagentur: token fetch failed: %s", exc)
            return []

        for query in queries:
            try:
                params = {
                    "was": query,
                    "wo": location,
                    "umkreis": "50",
                    "veroeffentlichtseit": "3",
                    "size": str(MAX_JOBS_PER_QUERY),
                    "page": "0",
                }
                data = self._search(params)

                for offer in data.get("stellenangebote") or []:
                    ref = offer.get("refnr", "")
                    job_id = ref or f"{offer.get('titel','')}{offer.get('arbeitgeber','')}"
                    if job_id in seen:
                        continue
                    seen.add(job_id)

                    url = offer.get("externeUrl") or (
                        f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref}"
                        if ref else ""
                    )
                    arbeitsort = offer.get("arbeitsort", {})
                    job_location = ", ".join(
                        filter(None, [arbeitsort.get("ort"), arbeitsort.get("region")])
                    ) or location

                    jobs.append({
                        "id": job_id,
                        "title": offer.get("titel", "").strip(),
                        "company": offer.get("arbeitgeber", "").strip(),
                        "location": job_location,
                        "url": url,
                        "description": (offer.get("stellenbeschreibung") or "")[:500].strip(),
                        "posted_date": offer.get("aktuelleVeroeffentlichungsdatum", ""),
                        "source": self.SOURCE_NAME,
                    })

            except Exception as exc:
                logger.error("Arbeitsagentur query '%s' failed: %s", query, exc)

            time.sleep(self.POLITE_DELAY)

        logger.info("Arbeitsagentur: %d jobs collected", len(jobs))
        return jobs
