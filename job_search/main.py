"""
Job Search Automation – Main entry point.

Run with:  python -m job_search.main
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Set

from .ai_scorer import score_jobs_with_ai
from .config import PROFILE, SEARCH_QUERIES
from .emailer import build_html, send_email
from .filter import is_relevant, score_job
from .scrapers.arbeitsagentur import ArbeitsagenturScraper
from .scrapers.indeed import IndeedScraper
from .scrapers.linkedin import LinkedInScraper
from .scrapers.stepstone import StepStoneScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("job_search")

SEEN_FILE = Path("data/seen_jobs.json")
MAX_SEEN_ENTRIES = 5000  # keep file size reasonable


# ── Deduplication helpers ────────────────────────────────────────────────────

def load_seen() -> Set[str]:
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text()))
        except Exception:
            pass
    return set()


def save_seen(seen: Set[str]) -> None:
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Keep only the most recent MAX_SEEN_ENTRIES to prevent unbounded growth
    trimmed = list(seen)[-MAX_SEEN_ENTRIES:]
    SEEN_FILE.write_text(json.dumps(trimmed, indent=2))


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("=== Job Search started – %s ===", datetime.now().strftime("%d.%m.%Y %H:%M"))

    seen = load_seen()
    location = PROFILE["location"]

    # GitHub Actions IPs are blocked or return HTML (bot-detection) for several
    # job boards. Only LinkedIn works reliably from CI.
    # Arbeitsagentur, Indeed, StepStone run locally where IPs are not flagged.
    in_ci = os.environ.get("CI", "").lower() == "true"
    if in_ci:
        logger.info(
            "CI detected – running LinkedIn only "
            "(Arbeitsagentur/Indeed/StepStone blocked by IP or bot-detection)"
        )
    scrapers = [
        LinkedInScraper(),
        *([] if in_ci else [ArbeitsagenturScraper(), IndeedScraper(), StepStoneScraper()]),
    ]

    raw_jobs: List[dict] = []
    for scraper in scrapers:
        try:
            jobs = scraper.fetch(SEARCH_QUERIES, location)
            logger.info("%s → %d jobs fetched", scraper.SOURCE_NAME, len(jobs))
            raw_jobs.extend(jobs)
        except Exception as exc:
            logger.error("%s scraper failed: %s", scraper.SOURCE_NAME, exc)

    logger.info("Total raw: %d | Already seen: %d", len(raw_jobs), len(seen))

    # De-duplicate against history
    new_jobs = [j for j in raw_jobs if j["id"] not in seen]
    logger.info("New (not seen before): %d", len(new_jobs))

    # Step 1: keyword pre-filter (fast, no API cost)
    candidates: List[dict] = []
    for job in new_jobs:
        s = score_job(job)
        if is_relevant(s):
            candidates.append({**job, "score": s})
    logger.info("Candidates after keyword filter: %d", len(candidates))

    # Step 2: AI re-scoring with full profile context (uses Claude API if key present)
    relevant = score_jobs_with_ai(candidates)

    # Re-apply minimum score after AI scoring (AI may lower some scores)
    relevant = [j for j in relevant if is_relevant(j["score"])]
    relevant.sort(key=lambda j: j["score"], reverse=True)
    logger.info("Relevant after AI scoring: %d", len(relevant))

    # Update deduplication state (mark all new jobs as seen, not just relevant ones)
    for job in new_jobs:
        seen.add(job["id"])
    save_seen(seen)

    # Send email
    if relevant:
        recipient = os.environ.get("RECIPIENT_EMAIL", PROFILE["email"])
        subject = (
            f"\U0001f50d {len(relevant)} neue Stelle{'n' if len(relevant) != 1 else ''} "
            f"f\u00fcr dich | {datetime.now().strftime('%d.%m.%Y')}"
        )
        html = build_html(relevant, PROFILE["name"])
        try:
            send_email(to=recipient, subject=subject, html=html)
            logger.info("Done – email with %d jobs sent to %s", len(relevant), recipient)
        except Exception as exc:
            logger.error("Failed to send email: %s", exc)
    else:
        logger.info("No relevant new jobs found today – no email sent.")


if __name__ == "__main__":
    main()
