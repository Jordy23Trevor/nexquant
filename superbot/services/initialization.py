import os
import sys
import threading
import traceback
from datetime import datetime
import logging
from superbot.config import (
    BROKER_TYPE, ALLOW_LIVE_TRADING,
    MIN_POSITION_SIZE, MAX_POSITION_SIZE, MAX_OPEN_POSITIONS,
    RISK_PCT, MAX_DAILY_LOSS_PCT, MAX_MONTHLY_LOSS_PCT,
    KELLY_FRACTION, MIN_TRADES_FOR_KELLY,
    SL_ATR_MULT, TP_ATR_MULT, TRAIL_ATR_MULT, BE_ATR_MULT,
    BE_DYN_RR, BE_DYN_RR_RATIO, COOLDOWN_SECONDS,
    EMA_FAST, EMA_SLOW, EMA_TREND, HTF_EMA, D1_EMA, W1_EMA,
    RSI_LEN, RSI_OB, RSI_OS,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    ADX_LEN, ADX_TREND, ST_MULTIPLIER, ST_ATR_LEN,
    ATR_LEN, BB_LEN, BB_STD,
    ICHIMOKU_TENKAN, ICHIMOKU_KIJUN, ICHIMOKU_SENKOU_SPAN_B, ICHIMOKU_DISPLACEMENT,
    VWAP_WINDOW, COMMISSION_PCT, SLIPPAGE_PCT, SCORE_MIN,
    CRYPTO_BLACKLIST, CRYPTO_SCORE_MIN, CRYPTO_BUY_BLOCK_BTC_DROP, CRYPTO_BNB_VOLUME_FACTOR,
    EMA_FAST_CRYPTO, EMA_SLOW_CRYPTO, ADX_TREND_CRYPTO, SCORE_MIN_CRYPTO,
    SL_ATR_MULT_CRYPTO, TP_ATR_MULT_CRYPTO,
    EMA_FAST_FOREX, EMA_SLOW_FOREX, ADX_TREND_FOREX, SCORE_MIN_FOREX,
    SL_ATR_MULT_FOREX, TP_ATR_MULT_FOREX, FOREX_NEWS_AVOID_MINUTES,
    EMA_FAST_STOCK, EMA_SLOW_STOCK, ADX_TREND_STOCK, SCORE_MIN_STOCK,
    SL_ATR_MULT_STOCK, TP_ATR_MULT_STOCK, ALLOW_SHORT_STOCK,
    NEWS_UPDATE_INTERVAL, NEWS_AVOIDANCE_BEFORE, NEWS_AVOIDANCE_AFTER,
    NEWS_RISK_REDUCTION_FACTOR, NEWS_HIGH_IMPACT_ONLY,
    FEAR_GREED_EXTREME_FEAR, FEAR_GREED_EXTREME_GREED, CRYPTOCOMPARE_API_KEY,
    ENABLE_DASHBOARD,
)
from superbot.broker import create_broker
from superbot.state import StateManager
from superbot.risk import RiskManager
from superbot.news import NewsManager
from superbot.indicators.technical_indicators import TechnicalIndicators
from superbot.strategy import TradingStrategy

log = logging.getLogger('initialization')
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from superbot.dashboard import Dashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False


def initialize_components(bot):

    """Initialise tous les composants du bot."""
    try:
        log.info("Initialisation des composants...")

        # 1. Synchronisation de la configuration Cloud & Télémétrie
        bot.remote_config = None
        active_broker_type = BROKER_TYPE
        broker_kwargs = {}

        if bot.telemetry.enabled:
            log.info("Tentative de synchronisation de la configuration cloud...")
            res = bot.telemetry.sync_config(current_version="v1.0.0")
            if res:
                if res.get("is_expired"):
                    log.error("❌ Licence expirée ou inactive. Le bot ne peut pas démarrer.")
                    sys.exit(1)
                if res.get("ok"):
                    bot.remote_config = res
                    log.info("Configuration cloud synchronisée avec succès.")

                    # Mettre à jour les paramètres de trading
                    cloud_cfg = res.get("config", {})
                    bot.adaptive_risk_pct = cloud_cfg.get("risk_pct", bot.adaptive_risk_pct)
                    bot.adaptive_score_min = cloud_cfg.get("score_min", bot.adaptive_score_min)

                    if not cloud_cfg.get("is_running", True):
                        bot.is_paused = True
                        log.info("⏸️ Le bot démarre en état de PAUSE (configuré ainsi sur le Cloud).")

                    # Récupérer les informations du Broker depuis le Cloud
                    broker_info = res.get("broker")
                    if broker_info:
                        active_broker_type = broker_info.get("broker_type", BROKER_TYPE)
                        # Si c'est MT5, rajouter les clés de connexion spécifiques
                        if active_broker_type == "mt5":
                            broker_kwargs["login"] = broker_info.get("login")
                            broker_kwargs["password"] = broker_info.get("password")
                            broker_kwargs["server"] = broker_info.get("server")
                            broker_kwargs["path"] = broker_info.get("path")
                        else:
                            broker_kwargs["api_key"] = broker_info.get("api_key")
                            broker_kwargs["api_secret"] = broker_info.get("api_secret")
                        log.info(f"Utilisation du broker configuré sur le Cloud : {active_broker_type}")

                    # Vérification des mises à jour
                    update_info = res.get("update", {})
                    if update_info.get("available"):
                        log.warning(f"🔔 Une nouvelle version du bot est disponible : {update_info.get('latest_version')}")
                        if update_info.get("mandatory"):
                            log.error("❌ Cette mise à jour est obligatoire. Veuillez mettre à jour le bot pour continuer.")
                            sys.exit(1)

        if bot.active_broker_type != active_broker_type:
            log.info(f"Le type de broker a changé de {bot.active_broker_type} à {active_broker_type}. Réinitialisation du StateManager...")
            bot.active_broker_type = active_broker_type
            state_file = os.path.join(root_dir, 'superbot', 'logs', f'state_{bot.active_broker_type}.json')
            bot.state_manager = StateManager(filepath=state_file, ttl_hours=24)
            bot.state_manager.load_state()
            bot.failed_execution_cooldowns = bot.state_manager.failed_execution_cooldowns
            bot.blocked_symbols = bot.state_manager.blocked_symbols
            bot.session_pnl_by_symbol = bot.state_manager.session_pnl_by_symbol
            bot.consecutive_losses = bot.state_manager.consecutive_losses
            bot._adaptation_counter = bot.state_manager.adaptation_counter

        log.info(f"Création du broker : {active_broker_type}")
        bot.broker = create_broker(active_broker_type, **broker_kwargs)
        log.info("Broker initialisé")

        try:
            acc_summary = bot.broker.get_account_summary()
            bot.initial_balance = float(acc_summary.get("equity") or acc_summary.get("balance") or bot.broker.get_balance())
            log.info(f"Solde/Équité initial détecté : {bot.initial_balance}")
        except Exception as e:
            log.warning(f"⚠️  Impossible de récupérer le solde initial via le résumé du compte : {e}")
            try:
                bot.initial_balance = bot.broker.get_balance()
                log.info(f"Solde initial détecté (fallback get_balance) : {bot.initial_balance}")
            except Exception as e2:
                log.warning(f"⚠️  Impossible de récupérer le solde initial : {e2}")
                bot.initial_balance = 10000.0

        # Déterminer les instruments selon le broker (clés spécifiques au broker en priorité)
        broker_type = active_broker_type  # "binance", "alpaca", "mt5"
        broker_key = f"INSTRUMENTS_{broker_type.upper()}"  # ex: INSTRUMENTS_MT5
        env_instruments_broker = os.getenv(broker_key)
        env_instruments_generic = os.getenv("INSTRUMENTS")

        if env_instruments_broker:
            bot.instruments = [s.strip() for s in env_instruments_broker.split(",") if s.strip()]
            log.info(f"Instruments spécifiques au broker ({broker_key}) : {bot.instruments}")
        elif env_instruments_generic:
            bot.instruments = [s.strip() for s in env_instruments_generic.split(",") if s.strip()]
            log.info(f"Instruments configurés via la variable générique INSTRUMENTS : {bot.instruments}")
        else:
            bot.instruments = bot.broker.get_default_instruments()
            log.info(f"Aucun instrument configuré — défauts courtier ({active_broker_type}) : {bot.instruments}")

        # 1.4 Filtre Multi-devises (Désactiver les paires croisées non-USD)
        supported_instruments = []
        for symbol in bot.instruments:
            normalized = symbol.upper().replace("/", "")
            # Pour Alpaca, pas de concept de paires de devises croisées (ce sont des actions/ETFs cotés en USD)
            if active_broker_type == "alpaca":
                supported_instruments.append(symbol)
            # Si le symbole finit par USD (ou USDT, USDC, BUSD) ou commence par USD, on l'accepte
            elif normalized.endswith("USD") or normalized.endswith("USDT") or normalized.endswith("USDC") or normalized.endswith("BUSD") or normalized.startswith("USD"):
                supported_instruments.append(symbol)
            else:
                log.warning(f"🚨 PAIRE CROISÉE DÉTECTÉE ({symbol}) : La conversion PnL automatique sans USD comme devise de base ou de cotation n'est pas supportée. Actif désactivé.")
        bot.instruments = supported_instruments

        news_broker_key = f"NEWS_ASSETS_{active_broker_type.upper()}"
        env_news_assets_broker = os.getenv(news_broker_key)
        env_news_assets_generic = os.getenv("NEWS_ASSETS")
        if env_news_assets_broker:
            bot.news_assets = [s.strip().upper() for s in env_news_assets_broker.split(",")]
            log.info(f"Actifs de nouvelles spécifiques au broker ({news_broker_key}) : {bot.news_assets}")
        elif env_news_assets_generic:
            bot.news_assets = [s.strip().upper() for s in env_news_assets_generic.split(",")]
            log.info(f"Actifs de nouvelles configurés via .env : {bot.news_assets}")
        else:
            bot.news_assets = bot.broker.get_default_news_assets()
            log.info(f"Actifs de nouvelles — défauts broker ({active_broker_type}) : {bot.news_assets}")

        # 2. Créer le gestionnaire de risques
        asset_type = bot.broker.get_asset_type()
        default_min_pos = MIN_POSITION_SIZE
        default_max_pos = MAX_POSITION_SIZE

        if asset_type == "forex":
            # Pour le forex, les tailles sont en unités de devise (ex: 1000 EUR)
            default_min_pos = 1.0
            default_max_pos = 10000000.0
        elif asset_type == "stock":
            # Pour les actions, les tailles sont en actions (ex: 1 action SPY = ~500 USD)
            default_min_pos = 0.001
            default_max_pos = 100000.0
        elif asset_type == "crypto":
            # Pour la crypto, les tailles sont en jetons (ex: 0.001 BTC, 0.1 SOL)
            default_min_pos = 0.001
            default_max_pos = 1000000.0

        # Permettre à l'utilisateur de surcharger via .env s'ils ont explicitement configuré ces variables
        env_min_pos = os.getenv("MIN_POSITION_SIZE")
        env_max_pos = os.getenv("MAX_POSITION_SIZE")
        actual_min_pos = float(env_min_pos) if env_min_pos else default_min_pos
        actual_max_pos = float(env_max_pos) if env_max_pos else default_max_pos

        # Déterminer le nombre maximum de positions selon le broker
        broker_type = BROKER_TYPE
        max_pos_key = f"MAX_OPEN_POSITIONS_{broker_type.upper()}"
        env_max_pos_broker = os.getenv(max_pos_key)
        if env_max_pos_broker:
            try:
                actual_max_open_positions = int(env_max_pos_broker)
                log.info(f"Nombre maximum de positions spécifique au broker ({max_pos_key}) : {actual_max_open_positions}")
            except ValueError:
                actual_max_open_positions = MAX_OPEN_POSITIONS
        else:
            actual_max_open_positions = MAX_OPEN_POSITIONS

        bot.risk_manager = RiskManager({
            'RISK_PCT': RISK_PCT,
            'MAX_DAILY_LOSS_PCT': MAX_DAILY_LOSS_PCT,
            'MAX_MONTHLY_LOSS_PCT': MAX_MONTHLY_LOSS_PCT,
            'MAX_OPEN_POSITIONS': actual_max_open_positions,
            'KELLY_FRACTION': KELLY_FRACTION,
            'MIN_TRADES_FOR_KELLY': MIN_TRADES_FOR_KELLY,
            'SL_ATR_MULT': SL_ATR_MULT,
            'TP_ATR_MULT': TP_ATR_MULT,
            'TRAIL_ATR_MULT': TRAIL_ATR_MULT,
            'BE_ATR_MULT': BE_ATR_MULT,
            'BE_DYN_RR': BE_DYN_RR,
            'BE_DYN_RR_RATIO': BE_DYN_RR_RATIO,
            'MIN_POSITION_SIZE': actual_min_pos,
            'MAX_POSITION_SIZE': actual_max_pos,
            'COOLDOWN_SECONDS': COOLDOWN_SECONDS,  # ✅ BUG FIX #5
        })
        log.info("Gestionnaire de risques initialisé")

        # Charger l'historique de trading réel (disque + broker)
        try:
            bot.risk_manager.load_trade_history_from_disk()
            broker_history = bot.broker.get_trade_history(days=30)
            if broker_history:
                bot.risk_manager.merge_broker_history(broker_history)
            log.info(f"Historique de trading final chargé : {len(bot.risk_manager.trade_history)} trades en mémoire.")
        except Exception as e:
            log.warning(f"Impossible de pré-charger l'historique de trading : {e}")

        # 3. Créer le calculateur d'indicateurs techniques
        bot.technical_indicators = TechnicalIndicators({
            'EMA_FAST': EMA_FAST,
            'EMA_SLOW': EMA_SLOW,
            'EMA_TREND': EMA_TREND,
            'HTF_EMA': HTF_EMA,
            'D1_EMA': D1_EMA,
            'W1_EMA': W1_EMA,
            'RSI_LEN': RSI_LEN,
            'RSI_OB': RSI_OB,
            'RSI_OS': RSI_OS,
            'MACD_FAST': MACD_FAST,
            'MACD_SLOW': MACD_SLOW,
            'MACD_SIGNAL': MACD_SIGNAL,
            'ADX_LEN': ADX_LEN,
            'ADX_TREND': ADX_TREND,
            'ST_MULTIPLIER': ST_MULTIPLIER,
            'ST_ATR_LEN': ST_ATR_LEN,
            'ATR_LEN': ATR_LEN,
            'BB_LEN': BB_LEN,
            'BB_STD': BB_STD,
            'ICHIMOKU_TENKAN': ICHIMOKU_TENKAN,
            'ICHIMOKU_KIJUN': ICHIMOKU_KIJUN,
            'ICHIMOKU_SENKOU_SPAN_B': ICHIMOKU_SENKOU_SPAN_B,
            'ICHIMOKU_DISPLACEMENT': ICHIMOKU_DISPLACEMENT,
            'VWAP_WINDOW': VWAP_WINDOW
        })
        log.info("Calculateur d'indicateurs techniques initialisé")

        # 4. Créer la stratégie de trading
        # Ajuster les commissions et slippage selon le broker actif pour éviter de brider le R:R
        actual_commission = COMMISSION_PCT
        actual_slippage = SLIPPAGE_PCT
        if bot.active_broker_type == "alpaca":
            actual_commission = 0.0  # Commission zéro sur Alpaca US Stocks/ETFs
        elif bot.active_broker_type == "binance":
            actual_commission = 0.04  # Commission moyenne Binance Futures (0.02% maker, 0.04% taker)

        bot.strategy = TradingStrategy({
            'SCORE_MIN': SCORE_MIN,
            'RISK_PCT': RISK_PCT,
            'KELLY_FRACTION': KELLY_FRACTION,
            'EMA_FAST': EMA_FAST,
            'EMA_SLOW': EMA_SLOW,
            'EMA_TREND': EMA_TREND,
            'HTF_EMA': HTF_EMA,
            'D1_EMA': D1_EMA,
            'W1_EMA': W1_EMA,
            'RSI_LEN': RSI_LEN,
            'RSI_OB': RSI_OB,
            'RSI_OS': RSI_OS,
            'MACD_FAST': MACD_FAST,
            'MACD_SLOW': MACD_SLOW,
            'MACD_SIGNAL': MACD_SIGNAL,
            'ADX_LEN': ADX_LEN,
            'ADX_TREND': ADX_TREND,
            'ST_MULTIPLIER': ST_MULTIPLIER,
            'ST_ATR_LEN': ST_ATR_LEN,
            'ATR_LEN': ATR_LEN,
            'BB_LEN': BB_LEN,
            'BB_STD': BB_STD,
            'ICHIMOKU_TENKAN': ICHIMOKU_TENKAN,
            'ICHIMOKU_KIJUN': ICHIMOKU_KIJUN,
            'ICHIMOKU_SENKOU_SPAN_B': ICHIMOKU_SENKOU_SPAN_B,
            'ICHIMOKU_DISPLACEMENT': ICHIMOKU_DISPLACEMENT,
            'VWAP_WINDOW': VWAP_WINDOW,
            # Filtres crypto — rapport post-mortem 2026-07-02
            'CRYPTO_BLACKLIST': CRYPTO_BLACKLIST,
            'CRYPTO_SCORE_MIN': CRYPTO_SCORE_MIN,
            'CRYPTO_BUY_BLOCK_BTC_DROP': CRYPTO_BUY_BLOCK_BTC_DROP,
            'CRYPTO_BNB_VOLUME_FACTOR': CRYPTO_BNB_VOLUME_FACTOR,
            'COMMISSION_PCT': actual_commission,
            'SLIPPAGE_PCT': actual_slippage,
            # ── Paramètres par classe d'actifs (refactoring stratégie 2026-07-14) ──
            'BROKER_TYPE': active_broker_type,
            # Crypto (Binance Futures)
            'EMA_FAST_CRYPTO': EMA_FAST_CRYPTO,
            'EMA_SLOW_CRYPTO': EMA_SLOW_CRYPTO,
            'ADX_TREND_CRYPTO': ADX_TREND_CRYPTO,
            'SCORE_MIN_CRYPTO': SCORE_MIN_CRYPTO,
            'SL_ATR_MULT_CRYPTO': SL_ATR_MULT_CRYPTO,
            'TP_ATR_MULT_CRYPTO': TP_ATR_MULT_CRYPTO,
            # Forex (MT5)
            'EMA_FAST_FOREX': EMA_FAST_FOREX,
            'EMA_SLOW_FOREX': EMA_SLOW_FOREX,
            'ADX_TREND_FOREX': ADX_TREND_FOREX,
            'SCORE_MIN_FOREX': SCORE_MIN_FOREX,
            'SL_ATR_MULT_FOREX': SL_ATR_MULT_FOREX,
            'TP_ATR_MULT_FOREX': TP_ATR_MULT_FOREX,
            'FOREX_NEWS_AVOID_MINUTES': FOREX_NEWS_AVOID_MINUTES,
            # ETF/Stocks (Alpaca)
            'EMA_FAST_STOCK': EMA_FAST_STOCK,
            'EMA_SLOW_STOCK': EMA_SLOW_STOCK,
            'ADX_TREND_STOCK': ADX_TREND_STOCK,
            'SCORE_MIN_STOCK': SCORE_MIN_STOCK,
            'SL_ATR_MULT_STOCK': SL_ATR_MULT_STOCK,
            'TP_ATR_MULT_STOCK': TP_ATR_MULT_STOCK,
            'ALLOW_SHORT_STOCK': ALLOW_SHORT_STOCK,
        }, indicators=bot.technical_indicators)
        log.info("Stratégie de trading initialisée")
        # Exposer le config au niveau bot pour les filtres de l'executor
        bot.config = bot.strategy.config

        # 5. Créer le gestionnaire de nouvelles
        bot.news_manager = NewsManager({
            'NEWS_ASSETS': bot.news_assets,
            'NEWS_UPDATE_INTERVAL': NEWS_UPDATE_INTERVAL,
            'NEWS_AVOIDANCE_BEFORE': NEWS_AVOIDANCE_BEFORE,
            'NEWS_AVOIDANCE_AFTER': NEWS_AVOIDANCE_AFTER,
            'NEWS_RISK_REDUCTION_FACTOR': NEWS_RISK_REDUCTION_FACTOR,
            'NEWS_HIGH_IMPACT_ONLY': NEWS_HIGH_IMPACT_ONLY,
            'FEAR_GREED_EXTREME_FEAR': FEAR_GREED_EXTREME_FEAR,
            'FEAR_GREED_EXTREME_GREED': FEAR_GREED_EXTREME_GREED,
            'CRYPTOCOMPARE_API_KEY': CRYPTOCOMPARE_API_KEY
        })
        log.info("Gestionnaire de nouvelles initialisé")

        # 5.5. Initialiser Prometheus Exporter (Phase 3.3)
        try:
            from superbot.telemetry import PrometheusExporter
            # Calculer un port de métriques unique pour éviter les conflits en multi-instances
            dash_port = int(os.environ.get("DASHBOARD_PORT", 5000))
            prom_port = int(os.getenv("PROMETHEUS_PORT", str(dash_port + 3000)))
            bot.prometheus = PrometheusExporter(port=prom_port)
            bot.prometheus.start()
        except Exception as e:
            bot.prometheus = None
            log.warning(f"Impossible d'initialiser Prometheus Exporter : {e}")

        # 6. Initialiser le dashboard si activé et disponible
        if ENABLE_DASHBOARD and DASHBOARD_AVAILABLE:
            try:
                dash_port = int(os.environ.get("DASHBOARD_PORT", 5000))
                bot.dashboard = Dashboard(port=dash_port, host="0.0.0.0")
                log.info(f"Dashboard initialisé sur le port {dash_port}")
            except Exception as e:
                log.warning(f"️  Impossible d'initialiser le dashboard : {e}")
                bot.dashboard = None
        else:
            log.info("Dashboard désactivé ou non disponible")

        # Synchroniser les positions initiales avec le broker
        try:
            bot._sync_positions_with_broker()
        except Exception as e:
            log.warning(f"Impossible de synchroniser les positions initiales : {e}")

        log.info("Tous les composants ont été initialisés avec succès")

    except Exception as e:
        log.error(f"Erreur lors de l'initialisation des composants : {e}")
        log.error(traceback.format_exc())
        raise