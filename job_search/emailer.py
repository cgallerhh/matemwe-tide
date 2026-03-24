"""
Build and send the daily HTML job-search digest via Gmail SMTP.
"""
import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

logger = logging.getLogger(__name__)

SOURCE_COLORS = {
    "Indeed": "#2557a7",
    "StepStone": "#e8620b",
    "LinkedIn": "#0077b5",
}


def _score_meta(score: int):
    """Return (label, color) for a relevance score."""
    if score >= 70:
        return "Sehr hoch", "#16a34a"
    if score >= 50:
        return "Hoch", "#65a30d"
    if score >= 35:
        return "Mittel", "#d97706"
    return "Relevant", "#2563eb"


def _ai_reason_html(job: Dict) -> str:
    reason = job.get("ai_reason", "")
    if not reason:
        return ""
    return (
        f'<p style="margin:8px 0 0;font-size:12px;color:#6366f1;font-style:italic;">'
        f'&#129302; KI-Bewertung: {reason}</p>'
    )


def _job_card(job: Dict) -> str:
    score = job.get("score", 0)
    label, score_color = _score_meta(score)
    source_color = SOURCE_COLORS.get(job.get("source", ""), "#6b7280")
    posted = job.get("posted_date", "")[:16] if job.get("posted_date") else ""
    desc = job.get("description", "")
    desc_html = ""
    if desc:
        snippet = desc[:360] + ("…" if len(desc) > 360 else "")
        desc_html = f"""
        <p style="margin:12px 0 16px;font-size:13px;color:#4b5563;line-height:1.65;
                  border-top:1px solid #f3f4f6;padding-top:12px;">{snippet}</p>"""

    posted_html = (
        f'<span style="font-size:12px;color:#9ca3af;">{posted}</span>'
        if posted
        else ""
    )

    return f"""
    <div style="background:#ffffff;border-radius:12px;padding:22px 24px;margin-bottom:18px;
                box-shadow:0 1px 4px rgba(0,0,0,0.08);border-left:4px solid {score_color};">

      <div style="display:flex;justify-content:space-between;align-items:flex-start;
                  margin-bottom:10px;flex-wrap:wrap;gap:6px;">
        <div>
          <span style="background:{source_color};color:#fff;padding:3px 8px;border-radius:4px;
                       font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;">
            {job.get("source", "")}
          </span>
          <span style="background:{score_color};color:#fff;padding:3px 10px;border-radius:4px;
                       font-size:11px;font-weight:700;margin-left:6px;">
            {score}/100 &mdash; {label}
          </span>
        </div>
        {posted_html}
      </div>

      <h2 style="margin:0 0 5px;font-size:17px;color:#111827;font-weight:700;line-height:1.35;">
        {job.get("title", "")}
      </h2>
      <p style="margin:0 0 6px;font-size:14px;color:#374151;font-weight:600;">
        {job.get("company") or "Unbekanntes Unternehmen"}
      </p>
      <p style="margin:0;font-size:13px;color:#6b7280;">
        &#128205; {job.get("location", "")}
      </p>
      {_ai_reason_html(job)}
      {desc_html}
      <a href="{job.get("url", "#")}"
         style="display:inline-block;background:#2563eb;color:#ffffff;padding:10px 20px;
                border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;
                margin-top:4px;">
        Jetzt bewerben &#8594;
      </a>
    </div>"""


def build_html(jobs: List[Dict], name: str) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    first_name = name.split()[0]
    count = len(jobs)

    source_counts = {}
    for j in jobs:
        s = j.get("source", "?")
        source_counts[s] = source_counts.get(s, 0) + 1
    sources_str = " &middot; ".join(
        f"{s}: {n}" for s, n in sorted(source_counts.items())
    )

    cards_html = "\n".join(_job_card(j) for j in jobs)

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Tagesübersicht Stellensuche {today}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">

  <div style="max-width:680px;margin:0 auto;padding:28px 16px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);
                border-radius:16px;padding:32px;margin-bottom:24px;text-align:center;">
      <h1 style="margin:0 0 8px;font-size:22px;color:#ffffff;font-weight:800;
                 letter-spacing:-.3px;">
        &#128269; Deine Stellen-Übersicht
      </h1>
      <p style="margin:0;font-size:15px;color:#bfdbfe;">
        {today} &nbsp;&middot;&nbsp; {count} relevante Stelle{"n" if count != 1 else ""} gefunden
      </p>
    </div>

    <!-- Intro -->
    <div style="background:#eff6ff;border-radius:12px;padding:16px 20px;margin-bottom:24px;
                border:1px solid #bfdbfe;">
      <p style="margin:0;font-size:14px;color:#1e40af;line-height:1.6;">
        <strong>Hallo {first_name}!</strong> Heute wurden
        <strong>{count} passende Stellen</strong> f&uuml;r dich gefunden
        und nach Relevanz sortiert.<br>
        <span style="font-size:12px;color:#3b82f6;">{sources_str}</span>
      </p>
    </div>

    <!-- Score legend -->
    <div style="background:#ffffff;border-radius:10px;padding:12px 16px;margin-bottom:24px;
                font-size:12px;color:#6b7280;display:flex;flex-wrap:wrap;gap:12px;
                border:1px solid #e5e7eb;">
      <span>&#9646; <strong style="color:#16a34a">70–100</strong> Sehr hoch</span>
      <span>&#9646; <strong style="color:#65a30d">50–69</strong> Hoch</span>
      <span>&#9646; <strong style="color:#d97706">35–49</strong> Mittel</span>
      <span>&#9646; <strong style="color:#2563eb">25–34</strong> Relevant</span>
    </div>

    <!-- Job cards -->
    {cards_html}

    <!-- Footer -->
    <div style="text-align:center;padding:24px 0 8px;border-top:1px solid #e5e7eb;
                margin-top:8px;">
      <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.7;">
        Automatisch generiert von deinem Job-Search-Bot<br>
        t&auml;glich 9:00 Uhr &nbsp;&middot;&nbsp; Quellen: Indeed &middot; StepStone &middot; LinkedIn<br>
        <a href="https://github.com/cgallerhh/matemwe-tide/actions"
           style="color:#93c5fd;text-decoration:none;">Workflow-Status ansehen</a>
      </p>
    </div>

  </div>
</body>
</html>"""


def send_email(to: str, subject: str, html: str) -> None:
    """Send HTML email via Gmail SMTP SSL (port 465)."""
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Job Search Bot <{user}>"
    msg["To"] = to

    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, password)
        server.sendmail(user, [to], msg.as_string())
    logger.info("Email sent to %s", to)
