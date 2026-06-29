"""
NexQuant Learning Engine v2
============================
Moteur de chargement et d'indexation des connaissances de trading.

Architecture (crescendo) :
  Niveau 1 : Murphy  — Fondations (lecture du marché, indicateurs, tendances)
  Niveau 2 : Elder   — Systèmes (Triple Screen, Iron Triangle, Impulse)
  Niveau 3 : Chan    — Quantitatif (Kelly, stationnarité, backtesting)

Usage :
    python resources/learning_engine.py               # traiter les nouveaux livres
    python resources/learning_engine.py --summary     # afficher les règles chargées
    python resources/learning_engine.py --reset       # reconstruire l'index complet

Le bot charge l'index au démarrage via :
    from resources.learning_engine import load_knowledge_index
    rules = load_knowledge_index()

Le bot peut filtrer par niveau :
    from resources.learning_engine import get_rules_by_level, get_rules_by_category
    foundation_rules = get_rules_by_level(1)     # Murphy
    risk_rules = get_rules_by_category("risk")
"""

import os
import sys
import json
import hashlib
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

log = logging.getLogger("learning_engine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Ajouter le répertoire parent (nexquant/) au sys.path pour les imports relatifs
_THIS_FILE = Path(__file__).resolve()
_NEXQUANT_ROOT = _THIS_FILE.parent.parent  # nexquant/
if str(_NEXQUANT_ROOT) not in sys.path:
    sys.path.insert(0, str(_NEXQUANT_ROOT))


# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
BOOKS_DIR  = BASE_DIR / "books"
KNOW_DIR   = BASE_DIR / "knowledge"
INDEX_FILE = BASE_DIR / "knowledge_index.json"

# ─── Catégories valides ───────────────────────────────────────────────────────
VALID_CATEGORIES = {
    "trend", "signal", "filter", "risk", "sizing", "strategy",
    "exit", "psychology", "performance",
}

VALID_REGIMES = {"TRENDING", "RANGING", "ALL"}


# ─── Chargement des modules de connaissances par livre ───────────────────────
def _load_book_modules() -> List[Dict[str, Any]]:
    """
    Charge les regles depuis les modules Python structures des livres.
    Ordre croissant de complexite (crescendo) : Niveau 1 -> Niveau 2 -> Niveau 3.
    11 livres integres sur 3 niveaux.
    """
    all_rules: List[Dict[str, Any]] = []

    # -- NIVEAU 1 : FONDATIONS -------------------------------------------------
    try:
        from resources.books_knowledge.murphy_technical_analysis import MURPHY_RULES
        all_rules.extend(MURPHY_RULES)
        log.info(f"  [Niveau 1] Murphy (Analyse Technique) -- {len(MURPHY_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module Murphy non trouve : {e}")

    try:
        from resources.books_knowledge.volman_price_action import VOLMAN_RULES
        all_rules.extend(VOLMAN_RULES)
        log.info(f"  [Niveau 1] Volman (Price Action) -- {len(VOLMAN_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module Volman non trouve : {e}")

    # -- NIVEAU 2 : SYSTEMES ---------------------------------------------------
    try:
        from resources.books_knowledge.elder_trading import ELDER_RULES
        all_rules.extend(ELDER_RULES)
        log.info(f"  [Niveau 2] Elder (Triple Screen) -- {len(ELDER_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module Elder non trouve : {e}")

    try:
        from resources.books_knowledge.kabbaj_art_trading import KABBAJ_RULES
        all_rules.extend(KABBAJ_RULES)
        log.info(f"  [Niveau 2] Kabbaj (L'Art du Trading) -- {len(KABBAJ_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module Kabbaj non trouve : {e}")

    try:
        from resources.books_knowledge.steenbarger_psychology import STEENBARGER_RULES
        all_rules.extend(STEENBARGER_RULES)
        log.info(f"  [Niveau 2] Steenbarger (Psychology 2.0) -- {len(STEENBARGER_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module Steenbarger non trouve : {e}")

    try:
        from resources.books_knowledge.montier_behavioral import MONTIER_RULES
        all_rules.extend(MONTIER_RULES)
        log.info(f"  [Niveau 2] Montier (Behavioral Investing) -- {len(MONTIER_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module Montier non trouve : {e}")

    try:
        from resources.books_knowledge.burniske_crypto import CRYPTO_RULES
        all_rules.extend(CRYPTO_RULES)
        log.info(f"  [Niveau 2] Burniske/Bruwer (Cryptoassets) -- {len(CRYPTO_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module Crypto non trouve : {e}")

    try:
        from resources.books_knowledge.contrarian_trading import CONTRARIAN_RULES
        all_rules.extend(CONTRARIAN_RULES)
        log.info(f"  [Niveau 2] Contrarian/Lustig -- {len(CONTRARIAN_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module Contrarian non trouve : {e}")

    # -- NIVEAU 3 : QUANTITATIF ------------------------------------------------
    try:
        from resources.books_knowledge.chan_algorithmic_trading import CHAN_RULES
        all_rules.extend(CHAN_RULES)
        log.info(f"  [Niveau 3] Chan (Algorithmic Trading) -- {len(CHAN_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module Chan non trouve : {e}")

    try:
        from resources.books_knowledge.ml_algo_trading import ML_RULES
        all_rules.extend(ML_RULES)
        log.info(f"  [Niveau 3] Jansen/Bissette/Koru (ML Algo) -- {len(ML_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module ML non trouve : {e}")

    try:
        from resources.books_knowledge.python_algo_advanced import PYTHON_ALGO_RULES
        all_rules.extend(PYTHON_ALGO_RULES)
        log.info(f"  [Niveau 3] Strimpel/Ratford/VanDerPost (Python Algo) -- {len(PYTHON_ALGO_RULES)} regles")
    except ImportError as e:
        log.warning(f"  Module Python Algo non trouve : {e}")

    log.info(f"\n  TOTAL : {len(all_rules)} regles chargees depuis 11 livres")
    return all_rules



# ─── Validation d'une règle ───────────────────────────────────────────────────
def _validate_rule(rule: Dict[str, Any]) -> bool:
    """Vérifie qu'une règle a les champs requis et des valeurs valides."""
    required = ["id", "level", "category", "rule", "author", "confidence"]
    for field in required:
        if field not in rule:
            log.warning(f"  ⚠️ Règle invalide — champ manquant '{field}': {rule.get('id', '?')}")
            return False

    if rule["level"] not in (1, 2, 3):
        log.warning(f"  ⚠️ Règle [{rule['id']}] — niveau invalide: {rule['level']}")
        return False

    if rule["category"] not in VALID_CATEGORIES:
        log.warning(f"  ⚠️ Règle [{rule['id']}] — catégorie invalide: {rule['category']}")
        return False

    if not (0.0 <= rule["confidence"] <= 1.0):
        log.warning(f"  ⚠️ Règle [{rule['id']}] — confidence hors range: {rule['confidence']}")
        return False

    for regime in rule.get("applicable_regimes", []):
        if regime not in VALID_REGIMES:
            log.warning(f"  ⚠️ Règle [{rule['id']}] — régime invalide: {regime}")
            return False

    return True


# ─── Extraction PDF (optionnel) ───────────────────────────────────────────────
def _extract_pdf_text(path: Path) -> str:
    """Extrait le texte brut d'un fichier PDF."""
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
        log.warning("pypdf non installé — extraction PDF désactivée. pip install pypdf")
        return ""
    except Exception as e:
        log.warning(f"Impossible d'extraire le texte de {path.name}: {e}")
        return ""


def _file_hash(path: Path) -> str:
    """Retourne le hash MD5 du fichier pour détection de changements."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _compute_modules_hash() -> str:
    """Hash combiné de tous les modules de connaissances pour invalider le cache."""
    books_knowledge_dir = BASE_DIR / "books_knowledge"
    combined = ""
    for py_file in sorted(books_knowledge_dir.glob("*.py")):
        if py_file.name != "__init__.py":
            combined += _file_hash(py_file)
    return hashlib.md5(combined.encode()).hexdigest()


# ─── Gestion de l'index ───────────────────────────────────────────────────────
def _load_index() -> Dict:
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "version": 2,
        "updated_at": None,
        "modules_hash": None,
        "books": {},
        "rules": [],
        "stats": {}
    }


def _save_index(index: Dict):
    index["updated_at"] = datetime.now().isoformat()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _build_stats(rules: List[Dict]) -> Dict:
    """Génère des statistiques sur les règles chargées."""
    stats: Dict[str, Any] = {
        "total": len(rules),
        "by_level": {},
        "by_category": {},
        "by_author": {},
        "by_regime": {},
        "filters": 0,
        "avg_confidence": 0.0,
    }

    total_conf = 0.0
    for rule in rules:
        level = str(rule.get("level", "?"))
        stats["by_level"][level] = stats["by_level"].get(level, 0) + 1

        cat = rule.get("category", "?")
        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        author = rule.get("author", "?")
        stats["by_author"][author] = stats["by_author"].get(author, 0) + 1

        for regime in rule.get("applicable_regimes", []):
            stats["by_regime"][regime] = stats["by_regime"].get(regime, 0) + 1

        impact = rule.get("parameter_impact", {})
        if impact.get("filter", False):
            stats["filters"] += 1

        total_conf += rule.get("confidence", 0.0)

    if rules:
        stats["avg_confidence"] = round(total_conf / len(rules), 3)

    return stats


# ─── Traitement principal ─────────────────────────────────────────────────────
def process_books(reset: bool = False) -> Dict:
    """
    Charge les règles depuis les modules Python structurés (books_knowledge/).
    Optionnellement, extrait aussi du texte des PDF dans books/ pour enrichissement futur.
    """
    KNOW_DIR.mkdir(parents=True, exist_ok=True)
    index = {
        "version": 2, "updated_at": None, "modules_hash": None,
        "books": {}, "rules": [], "stats": {}
    } if reset else _load_index()

    # Vérifier si les modules ont changé
    current_hash = _compute_modules_hash()
    if not reset and index.get("modules_hash") == current_hash and index.get("rules"):
        log.info(f"Index à jour (modules hash identique) — {len(index['rules'])} règles, aucune modification.")
        return index

    log.info("=" * 60)
    log.info("  NexQuant Learning Engine v2 — Chargement crescendo")
    log.info("=" * 60)

    # ── Étape 1: Charger les modules Python structurés ──────────────────────
    log.info("\n📚 Chargement des modules de connaissances...")
    raw_rules = _load_book_modules()

    # ── Étape 2: Valider et dédupliquer ─────────────────────────────────────
    validated: List[Dict] = []
    seen_ids = set()
    for rule in raw_rules:
        if not _validate_rule(rule):
            continue
        rule_id = rule["id"]
        if rule_id in seen_ids:
            log.warning(f"  ⚠️ Règle dupliquée ignorée : {rule_id}")
            continue
        seen_ids.add(rule_id)
        # Assurer la présence de champs par défaut
        rule.setdefault("applicable_regimes", ["ALL"])
        rule.setdefault("parameter_impact", {})
        rule.setdefault("keywords", [])
        rule.setdefault("actions", [])  # Sera rempli par le semantic classifier
        validated.append(rule)

    log.info(f"\n  ✅ {len(validated)} règles valides sur {len(raw_rules)} extraites")

    # ── Étape 3: Trier par niveau (crescendo) ───────────────────────────────
    validated.sort(key=lambda r: (r.get("level", 99), r.get("id", "")))

    # ── Étape 4: Mettre à jour l'index ──────────────────────────────────────
    index["rules"] = validated
    index["modules_hash"] = current_hash
    index["stats"] = _build_stats(validated)

    # ── Étape 5: Sauvegarder les connaissances par livre ────────────────────
    books_grouped: Dict[str, List[Dict]] = {}
    for rule in validated:
        book_key = rule.get("book", "Unknown")
        books_grouped.setdefault(book_key, []).append(rule)

    for book_name, book_rules in books_grouped.items():
        safe_name = "".join(c if c.isalnum() or c in " -._" else "_" for c in book_name)
        know_file = KNOW_DIR / (safe_name[:60] + ".json")
        level = book_rules[0].get("level", "?") if book_rules else "?"
        author = book_rules[0].get("author", "?") if book_rules else "?"
        with open(know_file, "w", encoding="utf-8") as f:
            json.dump({
                "book": book_name,
                "author": author,
                "level": level,
                "processed_at": datetime.now().isoformat(),
                "rules_count": len(book_rules),
                "rules": book_rules,
            }, f, ensure_ascii=False, indent=2)
        log.info(f"  💾 [{book_name[:50]}] → {know_file.name} ({len(book_rules)} règles)")

    # ── Étape 6: Sauvegarder l'index global ─────────────────────────────────
    _save_index(index)

    log.info(f"\n{'=' * 60}")
    log.info(f"  📊 Index global mis à jour : {len(validated)} règles")
    log.info(f"  📁 Fichier : {INDEX_FILE}")

    return index


# ─── API publique (utilisée par le bot au démarrage) ─────────────────────────
def load_knowledge_index() -> List[Dict]:
    """
    Retourne la liste complète des règles de trading depuis l'index.
    Reconstruit l'index si nécessaire ou si les modules ont changé.
    """
    # Si l'index n'existe pas ou est de l'ancienne version, le reconstruire
    if not INDEX_FILE.exists():
        process_books()
        return _load_index().get("rules", [])

    index = _load_index()

    # Vérifier la version et la cohérence du hash
    if index.get("version", 1) < 2:
        log.info("Index de l'ancienne version détecté — reconstruction...")
        process_books(reset=True)
        return _load_index().get("rules", [])

    # Vérifier si les modules ont changé
    try:
        current_hash = _compute_modules_hash()
        if index.get("modules_hash") != current_hash:
            log.info("Modules de connaissances modifiés — mise à jour de l'index...")
            process_books()
            return _load_index().get("rules", [])
    except Exception as e:
        log.warning(f"Impossible de vérifier le hash des modules : {e}")

    return index.get("rules", [])


def get_rules_by_category(category: str) -> List[Dict]:
    """Retourne les règles filtrées par catégorie."""
    return [r for r in load_knowledge_index() if r.get("category") == category]


def get_rules_by_level(level: int) -> List[Dict]:
    """Retourne les règles d'un niveau spécifique (1=Murphy, 2=Elder, 3=Chan)."""
    return [r for r in load_knowledge_index() if r.get("level") == level]


def get_rules_by_regime(regime: str) -> List[Dict]:
    """Retourne les règles applicables à un régime de marché donné."""
    return [
        r for r in load_knowledge_index()
        if regime in r.get("applicable_regimes", []) or "ALL" in r.get("applicable_regimes", [])
    ]


def get_filter_rules() -> List[Dict]:
    """Retourne uniquement les règles qui sont des filtres d'entrée obligatoires."""
    return [
        r for r in load_knowledge_index()
        if r.get("parameter_impact", {}).get("filter", False)
    ]


def get_rules_summary() -> Dict[str, int]:
    """Retourne un comptage des règles par catégorie."""
    rules = load_knowledge_index()
    summary: Dict[str, int] = {}
    for r in rules:
        cat = r.get("category", "unknown")
        summary[cat] = summary.get(cat, 0) + 1
    return summary


def get_index_stats() -> Dict:
    """Retourne les statistiques complètes de l'index."""
    index = _load_index()
    return index.get("stats", {})


# ─── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NexQuant Learning Engine v2")
    parser.add_argument("--reset",   action="store_true", help="Reconstruire l'index complet")
    parser.add_argument("--summary", action="store_true", help="Afficher le résumé des règles")
    parser.add_argument("--level",   type=int, help="Filtrer par niveau (1, 2, ou 3)")
    parser.add_argument("--filters", action="store_true", help="Afficher uniquement les filtres")
    args = parser.parse_args()

    index = process_books(reset=args.reset)
    stats = index.get("stats", {})

    if args.summary or args.level or args.filters:
        print("\n" + "=" * 60)
        print("  NexQuant Knowledge Base - Resume")
        print("=" * 60)
        print(f"\n  Total : {stats.get('total', 0)} regles")
        print(f"  Filtres obligatoires : {stats.get('filters', 0)}")
        print(f"  Confiance moyenne : {stats.get('avg_confidence', 0):.2%}")

        print("\n  Par niveau (crescendo) :")
        level_names = {"1": "Murphy - Fondations", "2": "Elder - Systemes", "3": "Chan - Quantitatif"}
        for lvl, count in sorted(stats.get("by_level", {}).items()):
            print(f"    Niveau {lvl} [{level_names.get(lvl, '?')}] : {count} regles")

        print("\n  Par categorie :")
        for cat, count in sorted(stats.get("by_category", {}).items()):
            print(f"    {cat:<16}: {count} regles")

        print("\n  Par auteur :")
        for author, count in sorted(stats.get("by_author", {}).items()):
            print(f"    {author:<40}: {count} regles")

        print("\n  Par regime :")
        for regime, count in sorted(stats.get("by_regime", {}).items()):
            print(f"    {regime:<12}: {count} regles")

        if args.level:
            rules = get_rules_by_level(args.level)
            level_names_full = {1: "Murphy", 2: "Elder", 3: "Chan"}
            print(f"\n  Regles de niveau {args.level} ({level_names_full.get(args.level, '?')}) :")
            for r in rules:
                filter_tag = " [FILTRE]" if r.get("parameter_impact", {}).get("filter") else ""
                print(f"    [{r['id']}]{filter_tag}")
                print(f"      -> {r['rule'][:100]}...")

        if args.filters:
            filter_rules = get_filter_rules()
            print(f"\n  Filtres d'entree obligatoires ({len(filter_rules)}) :")
            for r in filter_rules:
                print(f"    [{r['id']}] Niveau {r['level']} - {r['category']}")
                print(f"      -> {r.get('parameter_impact', {}).get('description', 'N/A')}")

        print(f"\n  Index : {INDEX_FILE}")
        print("=" * 60)
