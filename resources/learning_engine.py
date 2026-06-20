"""
NexQuant Learning Engine
========================
Parses trading books (PDF / TXT / MD) placed in resources/books/
and extracts actionable trading rules for the bot.

Usage:
    python resources/learning_engine.py               # process all new books
    python resources/learning_engine.py --summary     # print loaded rules
    python resources/learning_engine.py --reset       # rebuild full index

The bot loads the knowledge index at startup via:
    from resources.learning_engine import load_knowledge_index
    rules = load_knowledge_index()
"""

import os
import sys
import json
import hashlib
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

log = logging.getLogger("learning_engine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
BOOKS_DIR  = BASE_DIR / "books"
KNOW_DIR   = BASE_DIR / "knowledge"
INDEX_FILE = BASE_DIR / "knowledge_index.json"

# ─── Known authors and their key principles ───────────────────────────────────
AUTHOR_RULE_SEEDS: Dict[str, Dict] = {
    "elder": {
        "author":  "Dr. Alexander Elder",
        "source":  "Vivre du Trading",
        "rules": [
            {"id": "elder_triple_screen",    "category": "strategy",     "rule": "Triple Screen: weekly trend + daily oscillator + intraday entry."},
            {"id": "elder_2pct_rule",        "category": "risk",         "rule": "Never risk more than 2% of account equity on a single trade."},
            {"id": "elder_6pct_rule",        "category": "risk",         "rule": "Stop trading the month if monthly drawdown exceeds 6%."},
            {"id": "elder_macd_divergence",  "category": "signal",       "rule": "MACD divergence from price is a high-probability reversal signal."},
            {"id": "elder_force_index",      "category": "signal",       "rule": "Force Index (price * volume) confirms trend strength or weakness."},
            {"id": "elder_ema_envelope",     "category": "signal",       "rule": "Price outside EMA envelope signals overbought/oversold conditions."},
            {"id": "elder_iron_triangle",    "category": "risk",         "rule": "Iron Triangle: money management → entries → psychology (in that order)."},
        ]
    },
    "kabbaj": {
        "author":  "Thami Kabbaj",
        "source":  "L'Art du Trading",
        "rules": [
            {"id": "kabbaj_kelly",           "category": "sizing",       "rule": "Kelly Fraction: size = edge / odds. Use 25% of Kelly (fractional Kelly) to reduce ruin risk."},
            {"id": "kabbaj_rr_minimum",      "category": "risk",         "rule": "Minimum 2:1 reward-to-risk ratio on every trade entry."},
            {"id": "kabbaj_partial_tp",      "category": "exit",         "rule": "Take 50% profit at TP1, let the rest run with a trailing stop."},
            {"id": "kabbaj_price_action",    "category": "signal",       "rule": "Pure price action patterns (pin bars, engulfing) outperform indicators alone."},
            {"id": "kabbaj_sector_rotation", "category": "strategy",     "rule": "Follow capital rotation between sectors to anticipate trend changes."},
            {"id": "kabbaj_psychology",      "category": "psychology",   "rule": "Trading is 90% psychology. Discipline and routine create consistent results."},
        ]
    },
    "douglas": {
        "author":  "Mark Douglas",
        "source":  "Trading in the Zone",
        "rules": [
            {"id": "douglas_probability",    "category": "psychology",   "rule": "Think in probabilities. Each trade is a unique event within a series."},
            {"id": "douglas_edge",           "category": "strategy",     "rule": "Define your edge clearly. Execute it mechanically without hesitation."},
            {"id": "douglas_accept_risk",    "category": "psychology",   "rule": "Accept the risk BEFORE placing the trade. Eliminate hope and fear."},
            {"id": "douglas_consistency",    "category": "psychology",   "rule": "Consistency comes from executing your edge, not from being right."},
        ]
    },
    "van_tharp": {
        "author":  "Van Tharp",
        "source":  "Trade Your Way to Financial Freedom",
        "rules": [
            {"id": "tharp_sqn",              "category": "performance",  "rule": "System Quality Number (SQN) > 2.5 is good, > 5 is excellent."},
            {"id": "tharp_r_multiple",       "category": "risk",         "rule": "Express every trade as R-multiples. Expectancy > 0 over a large sample is the goal."},
            {"id": "tharp_position_sizing",  "category": "sizing",       "rule": "Position sizing is the most critical factor in overall performance."},
            {"id": "tharp_objectives",       "category": "strategy",     "rule": "Define your objectives before designing your system."},
        ]
    },
    "livermore": {
        "author":  "Jesse Livermore",
        "source":  "Reminiscences of a Stock Operator",
        "rules": [
            {"id": "livermore_trend",        "category": "strategy",     "rule": "The trend is your friend. Never trade against the primary trend."},
            {"id": "livermore_pyramiding",   "category": "sizing",       "rule": "Add to winning positions (pyramid) only when each unit is profitable."},
            {"id": "livermore_patience",     "category": "psychology",   "rule": "Sitting tight in a winning trade is harder than entering — do it anyway."},
            {"id": "livermore_pivot_points", "category": "signal",       "rule": "Buy at pivotal points where resistance turns support (breakout)."},
        ]
    },
    "schwager": {
        "author":  "Jack Schwager",
        "source":  "Market Wizards",
        "rules": [
            {"id": "schwager_risk_first",    "category": "risk",         "rule": "All great traders focus on risk management, not returns."},
            {"id": "schwager_methodology",   "category": "strategy",     "rule": "Have a clearly defined methodology. Follow it with discipline."},
            {"id": "schwager_cut_losses",    "category": "exit",         "rule": "Cut losses short, let profits run. The asymmetry is essential."},
            {"id": "schwager_market_type",   "category": "strategy",     "rule": "Adapt your approach to current market type (trending vs ranging)."},
        ]
    }
}

# ─── PDF text extraction (optional — requires pypdf) ─────────────────────────
def _extract_pdf_text(path: Path) -> str:
    """Extract raw text from a PDF file."""
    try:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages)
    except ImportError:
        log.warning("pypdf not installed — PDF text extraction disabled. Run: pip install pypdf")
        return ""
    except Exception as e:
        log.warning(f"Could not extract text from {path.name}: {e}")
        return ""


def _file_hash(path: Path) -> str:
    """Return MD5 hash of file content for change detection."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _match_author_rules(text: str) -> List[Dict]:
    """
    Scan text for known author keywords and return matched rule sets.
    This is a lightweight heuristic — replace with an LLM call for deeper extraction.
    """
    text_lower = text.lower()
    matched = []
    for key, data in AUTHOR_RULE_SEEDS.items():
        signals = [key, data["author"].lower().split()[0], data["source"].lower().split()[0]]
        if any(sig in text_lower for sig in signals):
            for rule in data["rules"]:
                r = dict(rule)
                r["author"] = data["author"]
                r["source"] = data["source"]
                matched.append(r)
    return matched


# ─── Index management ─────────────────────────────────────────────────────────
def _load_index() -> Dict:
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "updated_at": None, "books": {}, "rules": []}


def _save_index(index: Dict):
    index["updated_at"] = datetime.now().isoformat()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _seed_builtin_rules(index: Dict) -> Dict:
    """Inject built-in rules from known authors (always included)."""
    builtin_ids = {r["id"] for r in index["rules"]}
    added = 0
    for key, data in AUTHOR_RULE_SEEDS.items():
        for rule in data["rules"]:
            if rule["id"] not in builtin_ids:
                r = dict(rule)
                r["author"] = data["author"]
                r["source"] = data["source"]
                r["origin"] = "builtin"
                index["rules"].append(r)
                builtin_ids.add(rule["id"])
                added += 1
    if added:
        log.info(f"  {added} règles intégrées ajoutées à l'index")
    return index


# ─── Main processing ──────────────────────────────────────────────────────────
def process_books(reset: bool = False):
    """
    Scan resources/books/ and extract rules from any new or changed file.
    Supported formats: .pdf, .txt, .md
    """
    KNOW_DIR.mkdir(parents=True, exist_ok=True)

    index = {"version": 1, "updated_at": None, "books": {}, "rules": []} if reset else _load_index()

    # Always ensure built-in rules are present
    index = _seed_builtin_rules(index)

    book_files = list(BOOKS_DIR.glob("*.pdf")) + list(BOOKS_DIR.glob("*.txt")) + list(BOOKS_DIR.glob("*.md"))

    if not book_files:
        log.info(f"Aucun livre trouvé dans {BOOKS_DIR}. Placez vos PDF/TXT/MD ici.")
    else:
        log.info(f"{len(book_files)} livre(s) trouvé(s) dans {BOOKS_DIR}")

    for book_path in book_files:
        file_hash = _file_hash(book_path)
        book_key = book_path.name

        if not reset and book_key in index["books"] and index["books"][book_key]["hash"] == file_hash:
            log.info(f"  [{book_key}] inchangé — ignoré")
            continue

        log.info(f"  [{book_key}] traitement...")

        # Extract text
        if book_path.suffix.lower() == ".pdf":
            text = _extract_pdf_text(book_path)
        else:
            text = book_path.read_text(encoding="utf-8", errors="replace")

        # Match rules
        new_rules = _match_author_rules(text)

        # Save per-book knowledge file
        know_file = KNOW_DIR / (book_path.stem + ".json")
        with open(know_file, "w", encoding="utf-8") as f:
            json.dump({
                "book": book_key,
                "processed_at": datetime.now().isoformat(),
                "rules_found": len(new_rules),
                "rules": new_rules
            }, f, ensure_ascii=False, indent=2)

        # Merge into global index (deduplicate by id)
        existing_ids = {r["id"] for r in index["rules"]}
        added = 0
        for rule in new_rules:
            if rule["id"] not in existing_ids:
                rule["origin"] = book_key
                index["rules"].append(rule)
                existing_ids.add(rule["id"])
                added += 1

        index["books"][book_key] = {
            "hash": file_hash,
            "processed_at": datetime.now().isoformat(),
            "rules_extracted": len(new_rules),
            "path": str(book_path)
        }

        log.info(f"  [{book_key}] {len(new_rules)} règles extraites, {added} nouvelles")

    _save_index(index)
    log.info(f"Index mis à jour — {len(index['rules'])} règles au total ({INDEX_FILE})")
    return index


# ─── Public API (used by bot at startup) ──────────────────────────────────────
def load_knowledge_index() -> List[Dict]:
    """
    Returns the full list of trading rules from the knowledge index.
    Creates the index (with built-in rules) if it doesn't exist yet.
    """
    if not INDEX_FILE.exists():
        process_books()
    index = _load_index()
    return index.get("rules", [])


def get_rules_by_category(category: str) -> List[Dict]:
    """Returns rules filtered by category (risk, strategy, signal, sizing, exit, psychology)."""
    return [r for r in load_knowledge_index() if r.get("category") == category]


def get_rules_summary() -> Dict[str, int]:
    """Returns a count of rules per category."""
    rules = load_knowledge_index()
    summary: Dict[str, int] = {}
    for r in rules:
        cat = r.get("category", "unknown")
        summary[cat] = summary.get(cat, 0) + 1
    return summary


# ─── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NexQuant Learning Engine")
    parser.add_argument("--reset",   action="store_true", help="Rebuild full index")
    parser.add_argument("--summary", action="store_true", help="Print rule summary")
    args = parser.parse_args()

    index = process_books(reset=args.reset)

    if args.summary:
        print("\n=== Résumé des règles chargées ===")
        summary = get_rules_summary()
        for cat, count in sorted(summary.items()):
            print(f"  {cat:<14}: {count} règles")
        print(f"\n  TOTAL: {sum(summary.values())} règles")
        print(f"\n  Sources connues:")
        for key, data in AUTHOR_RULE_SEEDS.items():
            print(f"    - {data['author']} ({data['source']})")
        print("\nFichier index:", INDEX_FILE)
