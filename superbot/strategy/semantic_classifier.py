"""
NexQuant Semantic Rule Classifier
=================================
Uses sentence-transformers embeddings to automatically classify trading rules
from the knowledge base into actionable categories for the bot.

Replaces manual keyword matching with cosine-similarity–based NLP classification.

Usage:
    from superbot.strategy.semantic_classifier import SemanticRuleClassifier
    classifier = SemanticRuleClassifier()
    classified = classifier.classify_rules(knowledge_rules)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

log = logging.getLogger("semantic_classifier")

# ─── Action Categories ────────────────────────────────────────────────────────
# Each category maps a semantic description to a concrete bot parameter action.
# When a rule matches a category above the similarity threshold, the
# corresponding action modifier is applied during live trading.

ACTION_CATEGORIES = {
    "cap_kelly": {
        "description": (
            "Position sizing with Kelly criterion, half-Kelly, fractional Kelly, "
            "overbetting prevention, parameter estimation errors, bankroll management"
        ),
        "action": "CAP_KELLY",
        "modifier": 0.125,  # Cap kelly_fraction to this value
    },
    "cap_risk_2pct": {
        "description": (
            "Risk per trade limited to 2 percent of equity, maximum single trade risk, "
            "capital preservation, never risk more than two percent, account protection"
        ),
        "action": "CAP_RISK_PCT",
        "modifier": 2.0,  # Cap risk_pct to 2%
    },
    "bonus_ranging": {
        "description": (
            "Mean reversion strategy, ranging market conditions, stationarity test, "
            "ADF test, oversold overbought, support resistance bounce, Bollinger Band reversion"
        ),
        "action": "BONUS_SCORE_RANGING",
        "modifier": 0.5,  # +0.5 to score when market is RANGING
    },
    "bonus_trending": {
        "description": (
            "Trend following strategy, breakout setup, momentum trading, "
            "moving average crossover, high volume breakout, trend is your friend, pyramiding"
        ),
        "action": "BONUS_SCORE_TRENDING",
        "modifier": 0.5,  # +0.5 to score when market is TRENDING
    },
    "ema_squeeze": {
        "description": (
            "Price squeeze against EMA, compression near exponential moving average, "
            "double bends on 25 EMA, price build-up before breakout, tight consolidation"
        ),
        "action": "BONUS_EMA_SQUEEZE",
        "modifier": 0.5,  # +0.5 when EMA squeeze detected
    },
    "cut_losses": {
        "description": (
            "Cut losses short, strict stop loss discipline, exit losing trade quickly, "
            "don't hold losers, protective stop, trailing stop loss"
        ),
        "action": "ENFORCE_STRICT_SL",
        "modifier": 1.0,  # Flag — ensure SL is always set
    },
    "psychology_discipline": {
        "description": (
            "Trading psychology, emotional discipline, trading plan, "
            "consistency, patience, avoid revenge trading, think in probabilities"
        ),
        "action": "PSYCHOLOGY_FLAG",
        "modifier": 0.0,  # No direct parameter change — logged only
    },
}

# ─── Cache file for pre-computed classifications ──────────────────────────────
CACHE_DIR = Path(__file__).parent.parent / "resources"
CACHE_FILE = CACHE_DIR / "semantic_cache.json"


class SemanticRuleClassifier:
    """
    Classifies trading rules using sentence-transformer embeddings.
    Falls back to keyword matching if sentence-transformers is not installed.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", similarity_threshold: float = 0.40):
        """
        Args:
            model_name: HuggingFace sentence-transformer model name.
            similarity_threshold: Minimum cosine similarity to assign a category.
        """
        self.model_name = model_name
        self.threshold = similarity_threshold
        self._model = None
        self._category_embeddings = None
        self._use_nlp = False

        # Try loading sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name)
            self._use_nlp = True
            log.info(f"✅ Modèle NLP '{model_name}' chargé avec succès.")
            self._precompute_category_embeddings()
        except ImportError:
            log.warning(
                "⚠️ sentence-transformers non installé. "
                "Utilisation du classificateur par mots-clés (fallback). "
                "Pour activer le NLP : pip install sentence-transformers"
            )
        except Exception as e:
            log.warning(f"⚠️ Erreur lors du chargement du modèle NLP : {e}. Fallback mots-clés activé.")

    def _precompute_category_embeddings(self):
        """Pre-compute embeddings for all action category descriptions."""
        if not self._use_nlp:
            return
        from sentence_transformers import SentenceTransformer
        self._category_embeddings = {}
        for cat_name, cat_info in ACTION_CATEGORIES.items():
            self._category_embeddings[cat_name] = self._model.encode(
                cat_info["description"], convert_to_tensor=True
            )
        log.info(f"Embeddings pré-calculés pour {len(self._category_embeddings)} catégories d'action.")

    def classify_single_rule(self, rule_text: str) -> List[Dict[str, Any]]:
        """
        Classify a single rule text against all action categories.

        Returns:
            List of matched categories with their similarity scores and actions.
        """
        if self._use_nlp:
            return self._classify_nlp(rule_text)
        else:
            return self._classify_keywords(rule_text)

    def _classify_nlp(self, rule_text: str) -> List[Dict[str, Any]]:
        """NLP-based classification using cosine similarity."""
        from sentence_transformers import util as st_util

        rule_embedding = self._model.encode(rule_text, convert_to_tensor=True)
        matches = []

        for cat_name, cat_embedding in self._category_embeddings.items():
            similarity = float(st_util.cos_sim(rule_embedding, cat_embedding)[0][0])
            if similarity >= self.threshold:
                cat_info = ACTION_CATEGORIES[cat_name]
                matches.append({
                    "category": cat_name,
                    "action": cat_info["action"],
                    "modifier": cat_info["modifier"],
                    "similarity": round(similarity, 4),
                    "method": "nlp_embedding",
                })

        return matches

    def _classify_keywords(self, rule_text: str) -> List[Dict[str, Any]]:
        """Keyword-based fallback classification."""
        text = rule_text.lower()
        matches = []

        # Kelly / Position sizing
        if any(kw in text for kw in ["kelly", "half-kelly", "half kelly", "fractional kelly", "overbetting"]):
            matches.append({"category": "cap_kelly", "action": "CAP_KELLY", "modifier": 0.125, "similarity": 1.0, "method": "keyword"})

        # Risk 2%
        if any(kw in text for kw in ["2%", "two percent", "never risk more than"]):
            matches.append({"category": "cap_risk_2pct", "action": "CAP_RISK_PCT", "modifier": 2.0, "similarity": 1.0, "method": "keyword"})

        # Mean reversion / Ranging
        if any(kw in text for kw in ["stationarity", "mean-reversion", "mean reversion", "adf test", "ranging"]):
            matches.append({"category": "bonus_ranging", "action": "BONUS_SCORE_RANGING", "modifier": 0.5, "similarity": 1.0, "method": "keyword"})

        # Trend / Breakout
        if any(kw in text for kw in ["trend following", "breakout", "momentum", "trend is your friend", "pyramiding"]):
            matches.append({"category": "bonus_trending", "action": "BONUS_SCORE_TRENDING", "modifier": 0.5, "similarity": 1.0, "method": "keyword"})

        # EMA squeeze
        if any(kw in text for kw in ["squeeze", "25 ema", "double bends", "build-up", "compression"]):
            matches.append({"category": "ema_squeeze", "action": "BONUS_EMA_SQUEEZE", "modifier": 0.5, "similarity": 1.0, "method": "keyword"})

        # Cut losses
        if any(kw in text for kw in ["cut losses", "stop loss discipline", "exit losing", "protective stop"]):
            matches.append({"category": "cut_losses", "action": "ENFORCE_STRICT_SL", "modifier": 1.0, "similarity": 1.0, "method": "keyword"})

        # Psychology
        if any(kw in text for kw in ["psychology", "discipline", "probabilities", "consistency", "patience"]):
            matches.append({"category": "psychology_discipline", "action": "PSYCHOLOGY_FLAG", "modifier": 0.0, "similarity": 1.0, "method": "keyword"})

        return matches

    def classify_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classify all rules and attach action metadata to each one.

        Args:
            rules: List of rule dicts from knowledge_index.json

        Returns:
            Enriched list of rules with 'actions' field containing
            matched categories and their modifiers.
        """
        classified = []
        for rule_info in rules:
            rule_text = rule_info.get("rule", "")
            if not rule_text:
                classified.append(rule_info)
                continue

            actions = self.classify_single_rule(rule_text)
            enriched = dict(rule_info)
            enriched["actions"] = actions
            classified.append(enriched)

            if actions:
                action_names = [a["action"] for a in actions]
                log.debug(
                    f"  Règle [{rule_info.get('id', '?')}] → {action_names} "
                    f"(meilleure sim: {max(a['similarity'] for a in actions):.2f})"
                )

        log.info(
            f"Classification terminée : {sum(1 for r in classified if r.get('actions'))} / "
            f"{len(classified)} règles ont des actions assignées."
        )
        return classified

    def save_cache(self, classified_rules: List[Dict[str, Any]]):
        """Save classified rules to cache for instant reload."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(classified_rules, f, ensure_ascii=False, indent=2)
        log.info(f"Cache sémantique sauvegardé dans {CACHE_FILE}")

    def load_cache(self) -> Optional[List[Dict[str, Any]]]:
        """Load cached classification if available."""
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            log.info(f"Cache sémantique chargé ({len(cached)} règles).")
            return cached
        return None


# ─── CLI for standalone testing ───────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    # Add project root (nexquant/) to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    from resources.learning_engine import load_knowledge_index

    print("=" * 60)
    print("  NexQuant Semantic Rule Classifier — Test")
    print("=" * 60)

    classifier = SemanticRuleClassifier()
    rules = load_knowledge_index()

    print(f"\n📚 {len(rules)} règles chargées depuis knowledge_index.json\n")

    classified = classifier.classify_rules(rules)

    for rule in classified:
        actions = rule.get("actions", [])
        if actions:
            print(f"  ✅ [{rule['id']}] → {[a['action'] for a in actions]}")
            for a in actions:
                print(f"      ├─ {a['category']} (sim: {a['similarity']:.2f}, modifier: {a['modifier']}, méthode: {a['method']})")
        else:
            print(f"  ⬜ [{rule['id']}] → aucune action assignée")

    # Save cache
    classifier.save_cache(classified)
    print(f"\n💾 Cache sauvegardé dans {CACHE_FILE}")
