"""
Job search configuration – Christian Galler
Senior Sales Manager | GKV & Public Sector IT | Hamburg
"""

PROFILE = {
    "name": "Christian Galler",
    "email": "christian.galler@gmail.de",
    "location": "Hamburg",
    "radius_km": 50,
    "remote_ok": True,
    "salary_min": 90000,
}

# Search queries used on each job board
SEARCH_QUERIES = [
    "Senior Account Manager GKV",
    "Sales Manager Gesundheitswesen IT",
    "Key Account Manager Public Sector IT",
    "Business Development Manager Healthcare IT",
    "Account Executive eHealth",
    "Senior Sales Manager Krankenkasse",
    "Account Manager IT Consulting Gesundheit",
]

# Keywords that BOOST relevance score (keyword → points)
POSITIVE_KEYWORDS = {
    # Core domain – highest weight
    "GKV": 20,
    "gesetzliche Krankenversicherung": 20,
    "Krankenkasse": 18,
    "Krankenkassen": 18,
    "BKK": 15,
    "IKK": 15,
    "DAK": 15,
    "AOK": 15,
    "TK ": 10,
    "Public Sector": 15,
    "öffentlicher Sektor": 15,
    "Behörden": 10,
    "ÖGD": 12,
    # Sales roles
    "Account Manager": 15,
    "Sales Manager": 15,
    "Key Account": 15,
    "Business Development": 12,
    "Vertrieb": 10,
    "Neukundengewinnung": 10,
    "Großkunden": 10,
    "Enterprise Sales": 12,
    # IT & Health IT
    "eHealth": 15,
    "Gesundheitswesen": 12,
    "Healthcare IT": 15,
    "Health IT": 15,
    "IT-Consulting": 12,
    "IT Consulting": 12,
    "Digitalisierung": 8,
    "Digital Health": 14,
    # Tender / Bid
    "Ausschreibung": 15,
    "Vergabe": 12,
    "BID ": 10,
    "Tender": 10,
    "BAFO": 15,
    "Vergabeverfahren": 14,
    # Regulatory
    "KRITIS": 12,
    "NIS2": 12,
    "SGB V": 15,
    "TI 2.0": 12,
    "Telematikinfrastruktur": 12,
    # Technology
    "Cloud": 8,
    "BITMARCK": 15,
    "iskv": 12,
    "RPA": 8,
    "GenAI": 8,
    # Seniority / level
    "Senior": 8,
    "Lead ": 6,
    "Principal": 6,
    "Director": 5,
    "Head of": 5,
    # Location
    "Hamburg": 5,
    "Remote": 5,
    "Hybrid": 5,
    "Homeoffice": 5,
    # Known companies in the ecosystem
    "adesso": 8,
    "CGI": 8,
    "IBM": 6,
    "Sopra Steria": 8,
    "Capgemini": 8,
    "msg": 8,
    "Deloitte": 6,
    "PwC": 6,
    "KPMG": 6,
    "Accenture": 6,
    "T-Systems": 8,
    "Atruvia": 8,
}

# Keywords that REDUCE score (keyword → negative points)
NEGATIVE_KEYWORDS = {
    "Zeitarbeit": -30,
    "Zeitarbeitnehmer": -30,
    "Leiharbeit": -30,
    "Werkstudent": -40,
    "Praktikum": -40,
    "Praktikant": -40,
    "Trainee": -20,
    "Junior": -25,
    "Berufseinsteiger": -30,
    "Quereinsteiger": -20,
    "Minijob": -40,
    "450 ": -30,
    "Pflegefachkraft": -40,
    "Pflegekraft": -40,
    "Pflegehelfer": -40,
    "Arzt": -40,
    "Ärztin": -40,
    "Medizin": -20,
    "Krankenpflege": -40,
    "Physiotherap": -40,
    "Zahnarzt": -40,
    "Produktion": -30,
    "Lager ": -30,
    "Logistik": -20,
    "Fahrer": -35,
    "LKW": -35,
    "Monteur": -35,
    "Hausmeister": -40,
    "Reinigung": -40,
    "Buchhaltung": -20,
    "Steuerberater": -30,
}

# Minimum score to include in the daily email
MIN_SCORE = 25

# Max jobs fetched per query per source (avoid hammering)
MAX_JOBS_PER_QUERY = 25
