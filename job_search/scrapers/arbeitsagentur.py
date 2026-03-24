"""
Bundesagentur für Arbeit – offizielle, öffentliche REST-API.
Authentifizierung via OAuth2 Client Credentials (öffentlicher Client,
kein Secret erforderlich).

Dokumentation: https://jobsuche.api.bund.dev/
"""
import logging
import time
from typing import Dict, List, Optional

from ..config import MAX_JOBS_PER_QUERY
from .base import BaseScraper

logger = logging.getLogger(__name__)

TOKEN_URL = "https://rest.arbeitsagentur.de/oauth/token"
BASE_URL  = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
CLIENT_ID = "jobboerse-jobsuche"   # public client, no secret needed


class ArbeitsagenturScraper(BaseScraper):
    SOURCE_NAME = "Arbeitsagentur"
    POLITE_DELAY = 1.0

    def __init__(self) -> None:
        super().__init__()
        self._token: Optional[str] = None

    def _get_token(self) -> str:
        """Fetch a short-lived OAuth2 access token (client_credentials, no secret)."""
        resp = self.session.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials", "client_id": CLIENT_ID},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _auth_headers(self) -> Dict[str, str]:
        if not self._token:
            self._token = self._get_token()
        return {"Authorization": f"Bearer {self._token}"}

    def fetch(self, queries: List[str], location: str) -> List[Dict]:
        seen: set = set()
        jobs: List[Dict] = []

        try:
            self._token = self._get_token()
            logger.debug("Arbeitsagentur: OAuth token obtained")
        except Exception as exc:
            logger.error("Arbeitsagentur: could not obtain OAuth token: %s", exc)
            return []

        for query in queries:
            try:
                params = {
                    "was": query,
                    "wo": location,
                    "umkreis": "50",
                    "veroeffentlichtseit": "3",   # last 3 days (1 often returns 0 on weekends)
                    "angebotsart": "1",            # Arbeit (regular employment)
                    "size": str(MAX_JOBS_PER_QUERY),
                    "page": "0",
                }
                resp = self.get(
                    BASE_URL,
                    params=params,
                    headers=self._auth_headers(),
                )
                data = resp.json()

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
