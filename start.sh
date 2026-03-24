#!/bin/bash
# Jobsuche lokal starten
set -e

REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

# Python 3 prüfen
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3 nicht gefunden. Bitte installieren: https://www.python.org/downloads/"
  exit 1
fi

# .env prüfen
if [ ! -f ".env" ]; then
  echo "❌ Keine .env Datei gefunden."
  echo "   Erstelle sie so:"
  echo "   cp .env.example .env"
  echo "   Dann trage deine Werte in .env ein."
  exit 1
fi

# Virtuelle Umgebung erstellen (einmalig)
if [ ! -d ".venv" ]; then
  echo "→ Erstelle virtuelle Python-Umgebung..."
  python3 -m venv .venv
fi

# Abhängigkeiten installieren
echo "→ Installiere/prüfe Abhängigkeiten..."
.venv/bin/pip install -q -r requirements.txt

# Jobsuche starten
echo "→ Starte Jobsuche..."
echo ""
.venv/bin/python -m job_search.main
