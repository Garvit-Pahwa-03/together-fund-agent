"""
confidence.py
Calculates a confidence score (0-10) for each startup analysis.
Shows recruiters you understand LLM reliability.

Scoring logic:
- Website scraped successfully:     +3 points
- Founders named and verified:      +2 points
- Founded year confirmed:           +1 point
- Competitors named specifically:   +1 point
- AI architecture is specific:      +2 points
  (not generic phrases like "uses AI")
- HQ location confirmed:            +1 point
Max = 10 points
"""


GENERIC_ARCH_PHRASES = [
    "uses ai", "uses machine learning", "uses advanced ai",
    "ai-powered", "ml-based", "artificial intelligence",
    "deep learning", "neural network", "unknown",
    "not specified", "unclear", "likely uses"
]


def calculate_confidence(startup_data: dict) -> tuple[float, str]:
    """
    Returns (confidence_score, breakdown_string).
    startup_data keys: website_url, founders, founded_year,
    competitors, ai_architecture, hq_location,
    scrape_succeeded (bool)
    """
    score = 0.0
    breakdown = []

    # Website scraped successfully
    scrape_ok = startup_data.get("scrape_succeeded", False)
    if scrape_ok:
        score += 3.0
        breakdown.append("Website scraped: +3.0")
    else:
        breakdown.append("Website scraped: +0.0 (used search fallback)")

    # Founders named
    founders = startup_data.get("founders", "")
    if founders and founders.lower() not in (
        "not specified", "unknown", "not found", ""
    ):
        score += 2.0
        breakdown.append("Founders verified: +2.0")
    else:
        breakdown.append("Founders verified: +0.0 (not found)")

    # Founded year confirmed
    year = str(startup_data.get("founded_year", ""))
    if year and year.isdigit() and int(year) >= 2020:
        score += 1.0
        breakdown.append("Founded year confirmed: +1.0")
    else:
        breakdown.append("Founded year confirmed: +0.0")

    # Competitors named specifically
    competitors = startup_data.get("competitors", "")
    if competitors and len(competitors) > 20 and (
        "unknown" not in competitors.lower()
    ):
        score += 1.0
        breakdown.append("Competitors named: +1.0")
    else:
        breakdown.append("Competitors named: +0.0 (generic)")

    # AI architecture is specific
    arch = startup_data.get("ai_architecture", "").lower()
    is_generic = any(phrase in arch for phrase in GENERIC_ARCH_PHRASES)
    if arch and not is_generic and len(arch) > 15:
        score += 2.0
        breakdown.append("AI architecture specific: +2.0")
    else:
        score += 0.5
        breakdown.append("AI architecture specific: +0.5 (inferred)")

    # HQ location confirmed
    hq = startup_data.get("hq_location", "")
    if hq and hq.lower() not in ("not specified", "unknown", ""):
        score += 1.0
        breakdown.append("HQ location confirmed: +1.0")
    else:
        breakdown.append("HQ location confirmed: +0.0")

    score = min(round(score, 1), 10.0)
    breakdown_str = " | ".join(breakdown)
    return score, breakdown_str


def confidence_label(score: float) -> str:
    if score >= 8:
        return "High"
    elif score >= 5:
        return "Medium"
    else:
        return "Low"


def confidence_color(score: float) -> str:
    if score >= 8:
        return "#d1fae5"
    elif score >= 5:
        return "#fef3c7"
    else:
        return "#fee2e2"