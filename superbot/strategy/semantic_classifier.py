"""
NexQuant Semantic Rule Classifier v2
=====================================
Classifie les règles de la base de connaissances en actions concrètes
pour le bot de trading.

Nouvelles fonctionnalités v2 :
- Prise en compte des niveaux (1=Murphy, 2=Elder, 3=Chan)
- Nouvelles catégories d'actions : ENFORCE_MULTI_TIMEFRAME, REQUIRE_VOLUME_CONFIRM,
  PENALTY_COUNTER_TREND, ADJUST_SCORE_MIN, REJECT_NEGATIVE_KELLY
- Les règles de niveau 1 (filtres Murphy) sont appliquées comme conditions nécessaires
- Les règles de niveau 2 (Elder) modifient les scores
- Les règles de niveau 3 (Chan) ajustent le sizing mathématique

Usage :
    from superbot.strategy.semantic_classifier import SemanticRuleClassifier
    classifier = SemanticRuleClassifier()
    classified = classifier.classify_rules(knowledge_rules)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

log = logging.getLogger("semantic_classifier")

# ─── Catégories d'actions enrichies v2 ───────────────────────────────────────
# Chaque catégorie associe une description sémantique à une action concrète du bot.
# Les actions sont pondérées par le niveau de la règle source.

ACTION_CATEGORIES = {
    # ── GESTION DU RISQUE ─────────────────────────────────────────────────────
    "cap_kelly": {
        "description": (
            "Position sizing with Kelly criterion, half-Kelly, fractional Kelly, "
            "overbetting prevention, parameter estimation errors, bankroll management, "
            "optimal bet size, geometric growth rate maximization"
        ),
        "action": "CAP_KELLY",
        "modifier": 0.125,  # Kelly fraction plafonnée à 12.5% (half de 25%)
        "levels_applicable": [2, 3],
    },
    "cap_risk_2pct": {
        "description": (
            "Risk per trade limited to 2 percent of equity, maximum single trade risk, "
            "capital preservation, never risk more than two percent, account protection, "
            "Elder 2% rule, Iron Triangle money management"
        ),
        "action": "CAP_RISK_PCT",
        "modifier": 2.0,  # Risk_pct plafonné à 2%
        "levels_applicable": [1, 2, 3],
    },

    # ── BONUS DE SCORE PAR RÉGIME ─────────────────────────────────────────────
    "bonus_ranging": {
        "description": (
            "Mean reversion strategy, ranging market conditions, stationarity test, "
            "ADF test, oversold overbought, support resistance bounce, Bollinger Band reversion, "
            "cointegration, pairs trading, Hurst exponent below 0.5"
        ),
        "action": "BONUS_SCORE_RANGING",
        "modifier": 0.5,  # +0.5 au score si marché RANGING
        "levels_applicable": [1, 2, 3],
    },
    "bonus_trending": {
        "description": (
            "Trend following strategy, breakout setup, momentum trading, "
            "moving average crossover, high volume breakout, trend is your friend, pyramiding, "
            "Hurst exponent above 0.5, time series momentum, primary trend direction"
        ),
        "action": "BONUS_SCORE_TRENDING",
        "modifier": 0.5,  # +0.5 au score si marché TRENDING
        "levels_applicable": [1, 2, 3],
    },

    # ── SIGNAUX SPÉCIALISÉS ───────────────────────────────────────────────────
    "ema_squeeze": {
        "description": (
            "Price squeeze against EMA, compression near exponential moving average, "
            "double bends on 25 EMA, price build-up before breakout, tight consolidation, "
            "low volatility period before expansion, Bollinger Band squeeze"
        ),
        "action": "BONUS_EMA_SQUEEZE",
        "modifier": 0.5,  # +0.5 si EMA squeeze détecté
        "levels_applicable": [1, 2],
    },
    "volume_confirmation": {
        "description": (
            "Volume confirms the trend, volume should increase in trend direction, "
            "breakout requires volume spike, high volume validates breakout, "
            "volume divergence warns of weakening, OBV, Force Index, MFI"
        ),
        "action": "REQUIRE_VOLUME_CONFIRM",
        "modifier": 1.0,  # Flag — volume requis pour les signaux de breakout
        "levels_applicable": [1, 2],
    },
    "multi_timeframe": {
        "description": (
            "Multiple timeframe analysis, higher timeframe alignment, "
            "weekly trend determines direction, daily chart for timing, "
            "never trade against higher timeframe, Triple Screen System, "
            "timeframe hierarchy, long-term bias"
        ),
        "action": "ENFORCE_MULTI_TIMEFRAME",
        "modifier": 1.0,  # Flag — alignement HTF obligatoire
        "levels_applicable": [1, 2],
    },
    "counter_trend_penalty": {
        "description": (
            "Never trade against primary trend, trend is your friend, "
            "avoid counter-trend trades, impulse system red or blue bar, "
            "momentum opposing main direction, fighting the trend"
        ),
        "action": "PENALTY_COUNTER_TREND",
        "modifier": -1.5,  # Pénalité de score pour les trades contre-tendance
        "levels_applicable": [1, 2],
    },

    # ── FILTRES D'ENTRÉE ──────────────────────────────────────────────────────
    "cut_losses": {
        "description": (
            "Cut losses short, strict stop loss discipline, exit losing trade quickly, "
            "don't hold losers, protective stop, trailing stop loss, "
            "Elder stop below minor low, never move stop in wrong direction"
        ),
        "action": "ENFORCE_STRICT_SL",
        "modifier": 1.0,  # Flag — SL obligatoire à chaque trade
        "levels_applicable": [1, 2, 3],
    },
    "reject_no_edge": {
        "description": (
            "Negative Kelly fraction, no statistical edge, negative expected value, "
            "system quality number below threshold, insufficient win rate, "
            "strategy not statistically valid, skip trades with no edge"
        ),
        "action": "REJECT_NEGATIVE_KELLY",
        "modifier": 0.0,  # Refus total si Kelly < 0
        "levels_applicable": [3],
    },
    "volatility_scaling": {
        "description": (
            "Reduce position size during high volatility, momentum crash risk, "
            "VIX spike, volatility regime, fat tails, extreme loss protection, "
            "leverage reduction in crisis, vol-scaled position sizing"
        ),
        "action": "SCALE_SIZE_BY_VOLATILITY",
        "modifier": 0.5,  # Réduire la taille de 50% en régime haute volatilité
        "levels_applicable": [3],
    },

    # ── PSYCHOLOGIE ───────────────────────────────────────────────────────────
    "psychology_discipline": {
        "description": (
            "Trading psychology, emotional discipline, trading plan, "
            "consistency, patience, avoid revenge trading, think in probabilities, "
            "trading journal, fear and greed, mechanical execution"
        ),
        "action": "PSYCHOLOGY_FLAG",
        "modifier": 0.0,  # Pas de changement de parametres -- logge seulement
        "levels_applicable": [1, 2, 3],
    },

    # -- NOUVELLES CATEGORIES (Livres 4-11) ------------------------------------

    # Contrarian / sentiment extreme (Montier, Contrarian Trading)
    "contrarian_signal": {
        "description": (
            "Contrarian entry, fade the crowd, extreme sentiment, consensus opposite, "
            "RSI below 20 oversold, RSI above 80 overbought, capitulation volume, "
            "bearish divergence at top, bullish divergence at bottom, euphoria, panic"
        ),
        "action": "CONTRARIAN_SIGNAL",
        "modifier": 1.5,  # +1.5 si conditions contrarian alignees
        "levels_applicable": [2, 3],
    },

    # Breakout de volatilite (Kabbaj, Volman, ML)
    "volatility_breakout": {
        "description": (
            "Bollinger Band squeeze breakout, volatility compression expansion, "
            "Keltner Channel squeeze, narrow band breakout, BB width minimum, "
            "squeeze setup, build-up breakout, low ATR before spike"
        ),
        "action": "VOLATILITY_BREAKOUT",
        "modifier": 1.5,  # +1.5 si squeeze breakout confirme
        "levels_applicable": [1, 2, 3],
    },

    # Filtre crypto fondamental (Burniske)
    "crypto_fundamental": {
        "description": (
            "Crypto valuation, NVT ratio, on-chain metrics, active addresses, "
            "network value transactions, Metcalfe Law, Bitcoin dominance, "
            "halving cycle, crypto correlation, 24/7 market, altcoin, FOMO pump"
        ),
        "action": "CRYPTO_FUNDAMENTAL_FILTER",
        "modifier": 0.5,  # Filtre informatif
        "levels_applicable": [2, 3],
    },

    # Confiance ML (Jansen, Bissette)
    "ml_confidence": {
        "description": (
            "Machine learning model confidence, probability prediction, composite signal, "
            "Z-score trigger, VWAP deviation, Hidden Markov Model state, "
            "feature importance, walk-forward validation, ensemble model, factor signal"
        ),
        "action": "ML_CONFIDENCE_BOOST",
        "modifier": 1.0,  # +1.0 si signal ML confirme
        "levels_applicable": [3],
    },

    # Biais comportemental (Montier, Steenbarger)
    "behavioral_bias": {
        "description": (
            "Behavioral bias, confirmation bias, overconfidence, recency bias, "
            "loss aversion, anchoring, herding, cognitive error, psychological bias, "
            "FOMO dopamine, revenge trading, emotional decision"
        ),
        "action": "BEHAVIORAL_BIAS_PENALTY",
        "modifier": -0.5,  # -0.5 si biais comportemental detecte
        "levels_applicable": [2, 3],
    },

    # Protection losing streak (Steenbarger)
    "losing_streak_protection": {
        "description": (
            "Consecutive losses, losing streak, 3 losses in a row, 5 consecutive losses, "
            "reduce position after losses, drawdown protection, degraded performance, "
            "strategy review after losses, market regime change signal"
        ),
        "action": "LOSING_STREAK_PROTECTION",
        "modifier": 0.5,  # Reduire kelly a 50% apres losing streak
        "levels_applicable": [2, 3],
    },
}

# ─── Fichier de cache ─────────────────────────────────────────────────────────
CACHE_DIR = Path(__file__).parent.parent / "resources"
CACHE_FILE = CACHE_DIR / "semantic_cache.json"


class SemanticRuleClassifier:
    """
    Classifie les règles de trading via sentence-transformer embeddings (NLP)
    ou par mots-clés en fallback.

    Nouveauté v2 : les actions sont pondérées par le niveau de la règle source.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", similarity_threshold: float = 0.38):
        """
        Args:
            model_name: Modele HuggingFace sentence-transformer.
            similarity_threshold: Similarite cosinus minimale pour assigner une categorie.
        """
        self.model_name = model_name
        self.threshold = similarity_threshold
        self._model = None
        self._category_embeddings = None
        self._use_nlp = False
        self._nlp_initialized = False

    def _init_nlp(self):
        """Initialise le modele NLP de maniere paresseuse (lazy loading)."""
        if self._nlp_initialized:
            return
        self._nlp_initialized = True
        try:
            from sentence_transformers import SentenceTransformer
            log.info(f"Chargement paresseux du modele NLP '{self.model_name}'...")
            self._model = SentenceTransformer(self.model_name)
            self._use_nlp = True
            log.info(f"✅ Modele NLP '{self.model_name}' charge avec succes.")
            self._precompute_category_embeddings()
        except ImportError:
            log.warning(
                "⚠️ sentence-transformers non installe. "
                "Utilisation du classificateur par mots-cles (fallback). "
                "Pour activer le NLP : pip install sentence-transformers"
            )
        except Exception as e:
            log.warning(f"⚠️ Erreur lors du chargement du modele NLP : {e}. Fallback mots-cles active.")

    def _precompute_category_embeddings(self):
        """Pre-calcule les embeddings de toutes les descriptions de categories."""
        if not self._use_nlp:
            return
        self._category_embeddings = {}
        for cat_name, cat_info in ACTION_CATEGORIES.items():
            self._category_embeddings[cat_name] = self._model.encode(
                cat_info["description"], convert_to_tensor=True
            )
        log.info(f"Embeddings pre-calcules pour {len(self._category_embeddings)} categories d'action.")


    def classify_single_rule(self, rule_text: str, rule_level: int = 2) -> List[Dict[str, Any]]:
        """
        Classifie une regle en actions concretes.

        Args:
            rule_text: Texte de la regle
            rule_level: Niveau de la regle (1=Murphy, 2=Elder, 3=Chan)

        Returns:
            Liste des actions matchees avec leurs modificateurs ponderes par le niveau.
        """
        self._init_nlp()
        if self._use_nlp:
            matches = self._classify_nlp(rule_text)
        else:
            matches = self._classify_keywords(rule_text)


        # Filtrer les actions selon les niveaux applicables
        filtered = []
        for match in matches:
            cat_name = match.get("category", "")
            cat_info = ACTION_CATEGORIES.get(cat_name, {})
            applicable_levels = cat_info.get("levels_applicable", [1, 2, 3])
            if rule_level in applicable_levels:
                # Pondérer le modifier par le niveau (niveau 2 et 3 ont plus de poids)
                level_weight = {1: 0.8, 2: 1.0, 3: 1.2}.get(rule_level, 1.0)
                adj_match = dict(match)
                # Seulement ajuster les modifiers positifs (pas les pénalités)
                if adj_match["modifier"] > 0:
                    adj_match["modifier"] = round(adj_match["modifier"] * level_weight, 4)
                adj_match["rule_level"] = rule_level
                filtered.append(adj_match)

        return filtered

    def _classify_nlp(self, rule_text: str) -> List[Dict[str, Any]]:
        """Classification NLP par similarité cosinus."""
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
        """Classification par mots-clés (fallback sans NLP)."""
        text = rule_text.lower()
        matches = []

        keyword_map = {
            "cap_kelly": [
                "kelly", "half-kelly", "half kelly", "fractional kelly",
                "overbetting", "optimal bet", "geometric growth"
            ],
            "cap_risk_2pct": [
                "2%", "two percent", "never risk more than", "2 percent", "iron triangle"
            ],
            "bonus_ranging": [
                "stationarity", "mean-reversion", "mean reversion", "adf test",
                "ranging", "cointegration", "oversold overbought", "hurst"
            ],
            "bonus_trending": [
                "trend following", "breakout", "momentum", "trend is your friend",
                "pyramiding", "primary trend", "moving average crossover"
            ],
            "ema_squeeze": [
                "squeeze", "25 ema", "double bends", "build-up",
                "compression", "tight consolidation", "low volatility"
            ],
            "volume_confirmation": [
                "volume", "confirm", "volume spike", "force index", "obv",
                "money flow", "mfi", "volume breakout"
            ],
            "multi_timeframe": [
                "triple screen", "weekly", "timeframe", "higher timeframe",
                "long-term bias", "multi-timeframe", "weekly trend"
            ],
            "counter_trend_penalty": [
                "never trade against", "against the trend", "impulse system",
                "red bar", "blue bar", "counter-trend", "fighting the trend"
            ],
            "cut_losses": [
                "cut losses", "stop loss discipline", "exit losing",
                "protective stop", "never hold losers", "trailing stop"
            ],
            "reject_no_edge": [
                "negative kelly", "no edge", "negative expected value",
                "no statistical edge", "skip trade", "sqn"
            ],
            "volatility_scaling": [
                "volatility", "momentum crash", "vix", "fat tails",
                "leverage reduction", "vol-scaled", "high volatility regime"
            ],
            "psychology_discipline": [
                "psychology", "discipline", "probabilities", "consistency",
                "patience", "revenge trading", "fear", "greed", "journal"
            ],
            # -- Nouvelles categories (livres 4-11) -------------------------
            "contrarian_signal": [
                "contrarian", "fade the crowd", "capitulation", "extreme sentiment",
                "RSI below 20", "RSI above 80", "euphoria", "panic", "divergence at",
            ],
            "volatility_breakout": [
                "bollinger band squeeze", "squeeze breakout", "narrow band",
                "BB width", "build-up breakout", "volatility compression",
                "keltner squeeze"
            ],
            "crypto_fundamental": [
                "NVT", "on-chain", "active addresses", "halving", "bitcoin dominance",
                "BTC.D", "altcoin season", "metcalfe", "cryptoasset", "24/7"
            ],
            "ml_confidence": [
                "machine learning", "model confidence", "Z-score", "VWAP deviation",
                "HMM", "hidden markov", "composite signal", "walk-forward", "factor"
            ],
            "behavioral_bias": [
                "confirmation bias", "overconfidence", "recency bias", "loss aversion",
                "anchoring", "herding", "FOMO", "dopamine", "cognitive error"
            ],
            "losing_streak_protection": [
                "consecutive losses", "losing streak", "3 consecutive", "5 consecutive",
                "reduce after losses", "degraded performance", "win streak"
            ],
        }

        for cat_name, keywords in keyword_map.items():
            if any(kw.lower() in text for kw in keywords):
                cat_info = ACTION_CATEGORIES[cat_name]
                matches.append({
                    "category": cat_name,
                    "action": cat_info["action"],
                    "modifier": cat_info["modifier"],
                    "similarity": 1.0,
                    "method": "keyword",
                })

        return matches


    def classify_rules(self, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classifie toutes les règles et leur attache des actions concrètes.

        Args:
            rules: Liste de règles depuis knowledge_index.json

        Returns:
            Liste enrichie avec le champ 'actions' contenant les modifications.
        """
        classified = []
        actions_assigned = 0

        for rule_info in rules:
            rule_text = rule_info.get("rule", "")
            rule_level = rule_info.get("level", 2)

            if not rule_text:
                classified.append(rule_info)
                continue

            actions = self.classify_single_rule(rule_text, rule_level)

            # Fusionner avec les actions pré-définies dans parameter_impact
            impact = rule_info.get("parameter_impact", {})
            if impact.get("filter", False) and not any(
                a["action"] == "ENFORCE_STRICT_SL" for a in actions
            ):
                # Ajouter une action générique de filtre si pas déjà présente
                pass  # Les filtres sont gérés directement via parameter_impact

            enriched = dict(rule_info)
            enriched["actions"] = actions
            classified.append(enriched)

            if actions:
                actions_assigned += 1
                action_names = [a["action"] for a in actions]
                log.debug(
                    f"  Règle [Niv.{rule_level}][{rule_info.get('id', '?')}] → {action_names} "
                    f"(meilleure sim: {max(a['similarity'] for a in actions):.2f})"
                )

        log.info(
            f"Classification terminée : {actions_assigned}/{len(classified)} règles ont des actions. "
            f"Méthode: {'NLP' if self._use_nlp else 'mots-clés'}"
        )
        return classified

    def save_cache(self, classified_rules: List[Dict[str, Any]]):
        """Sauvegarde les règles classifiées en cache."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "version": 2,
            "saved_at": __import__("datetime").datetime.now().isoformat(),
            "rule_count": len(classified_rules),
            "rules": classified_rules,
        }
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        log.info(f"Cache sémantique v2 sauvegardé dans {CACHE_FILE} ({len(classified_rules)} règles)")

    def load_cache(self) -> Optional[List[Dict[str, Any]]]:
        """Charge le cache de classification si disponible et valide (v2)."""
        if not CACHE_FILE.exists():
            return None
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Vérifier la version du cache
            if cache_data.get("version", 1) < 2:
                log.info("Cache sémantique de l'ancienne version — reconstruction...")
                return None

            cached = cache_data.get("rules", [])
            log.info(f"Cache sémantique v2 chargé ({len(cached)} règles).")
            return cached
        except Exception as e:
            log.warning(f"Erreur lors du chargement du cache sémantique : {e}")
            return None


# ─── CLI pour tests autonomes ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    from resources.learning_engine import load_knowledge_index

    print("=" * 70)
    print("  NexQuant Semantic Rule Classifier v2 - Test Crescendo")
    print("=" * 70)

    classifier = SemanticRuleClassifier()
    rules = load_knowledge_index()

    print(f"\n{len(rules)} regles chargees depuis knowledge_index.json")

    # Classifier par niveau pour voir l'effet crescendo
    for level in [1, 2, 3]:
        level_rules = [r for r in rules if r.get("level") == level]
        level_names = {1: "Murphy (Fondations)", 2: "Elder (Systemes)", 3: "Chan (Quantitatif)"}
        print(f"\n-- Niveau {level} - {level_names.get(level, '?')} ({len(level_rules)} regles) --")

        classified_level = classifier.classify_rules(level_rules)
        for rule in classified_level:
            actions = rule.get("actions", [])
            filter_flag = " [FILTRE]" if rule.get("parameter_impact", {}).get("filter") else ""
            if actions:
                print(f"  OK [{rule['id']}]{filter_flag}")
                for a in actions:
                    print(f"      +- {a['action']} (modifier={a['modifier']}, sim={a['similarity']:.2f})")
            else:
                print(f"  -- [{rule['id']}]{filter_flag} -> aucune action")

    # Sauvegarder le cache
    all_classified = classifier.classify_rules(rules)
    classifier.save_cache(all_classified)
    print(f"\nCache sauvegarde dans {CACHE_FILE}")

