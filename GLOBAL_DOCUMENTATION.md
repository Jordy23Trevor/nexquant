# NexQuant — Global Multilingual Documentation

This is the unified document containing all guides, user manuals, and technical specifications for NexQuant in English, French, and Spanish.

For an interactive, premium reading experience with language selectors, search bar, and clean layout, open **[GLOBAL_DOCUMENTATION.html](GLOBAL_DOCUMENTATION.html)** in your web browser.

---


# ====================================================================
# LANGUAGE: FRANÇAIS
# ====================================================================


# 📖 Manuel d'Utilisation Complet - SuperBot Trading Unifié

## 1. Présentation du SuperBot
Le **SuperBot Trading Unifié** est un système de trading algorithmique de niveau institutionnel conçu pour fonctionner de manière autonome sur plusieurs classes d'actifs (Crypto, Actions, Forex).
Il combine l'analyse technique multi-indicateurs, un filtre sémantique NLP pour l'ingestion de règles textuelles de trading, et un gestionnaire de risques basé sur les règles de Kelly et d'Elder.

## 2. Prérequis Système
- **Python** : Version 3.8 ou supérieure (recommandé 3.10).
- **Dépendances** : `pandas`, `numpy`, `requests`, `python-dotenv`.
- **Dépendances optionnelles** : `sentence-transformers` (NLP local), `optuna` (Optimisation).

## 3. Installation et Lancement
1. Clonez ou téléchargez le projet.
2. Installez les packages :
   ```bash
   pip install -r requirements.txt
   ```
3. Configurez votre fichier `.env` à la racine du projet.
4. Lancez le bot :
   ```bash
   python superbot/main.py
   ```

## 4. Configuration (.env)
Les paramètres clés du fichier `.env` :
- `BROKER_TYPE` : Le courtier actif (`binance`, `alpaca`, `paper_forex`).
- `RISK_PCT` : Le pourcentage de capital risqué par position (par défaut `1.0`%).
- `SCORE_MIN` : Le score minimum (sur 10) requis pour déclencher un signal.
- `ENABLE_DASHBOARD` : Active le tableau de bord web (`http://localhost:5000`).
        


# 📈 Guide Expert Trader - Compréhension Avancée

## 1. Philosophie Centrale : Instinct-Raison-Connaissance
Le bot fonctionne en mariant trois types d'analyses :
1. **L'Instinct** : Traitement du sentiment de marché (Fear & Greed, nouvelles).
2. **La Raison** : Scoring technique strict basé sur 20+ indicateurs.
3. **La Connaissance** : Ingestion sémantique NLP de règles théoriques issues de la littérature financière (Ernest Chan, Alexander Elder, Bob Volman).

## 2. Optimisations de Performance et Réactivité
Pour maximiser la réactivité dans des marchés volatils, plusieurs paramètres ont été optimisés :
- **Seuil de score réduit** à `4` (au lieu de 6) pour attraper les retournements précoces.
- **Seuil ADX** ajusté à `20` pour détecter le début des mouvements de tendance plus tôt.
- **Pyramiding** (`USE_PYRAMIDING=true`) activé pour accumuler des positions sur les tendances fortes.
- **Filtre de volatilité** (`USE_VOLATILITY_FILTER=true`) exigeant au moins 0.5% d'amplitude pour éviter de se faire piéger dans les marchés plats (chop).
        


# 💻 Documentation Technique Complète

## 1. Architecture Modulaire
Le système est divisé en modules indépendants coordonnés par le moteur central `superbot/main.py` :
- **Broker Adapter Layer** (`superbot/broker/`) : Standardise les connexions API vers Binance, Alpaca et le simulateur Forex.
- **Risk Manager** (`superbot/risk/`) : Contrôle de l'exposition globale et du drawdown maximal.
- **Technical Indicators Engine** (`superbot/indicators/`) : Calculs vectorisés haute performance en O(N) pour les indicateurs (EMA, RSI, MACD, Bollinger Bands, ATR, Supertrend).
- **Semantic Classifier** (`superbot/strategy/semantic_classifier.py`) : Classifieur NLP utilisant des embeddings sémantiques.

## 2. Classifieur Sémantique NLP
Le classifieur charge les règles extraites des livres, génère leurs embeddings à l'aide de `sentence-transformers` et calcule leur similarité cosinus avec des profils d'action prédéfinis :
- `CAP_KELLY` : Plafonne la fraction de Kelly à 0.125.
- `CAP_RISK_PCT` : Limite le risque maximal par trade à 2%.
- `BONUS_SCORE_RANGING` / `BONUS_SCORE_TRENDING` : Ajuste dynamiquement le score selon le régime de marché détecté.

## 3. Optimisation Bayésienne (Optuna)
Le script `optimize_rules.py` permet d'ajuster automatiquement les poids des règles et les hyperparamètres (comme le score min) en effectuant des simulations de backtest rapides et en évaluant le Sharpe Ratio.
        


# 🔗 Changement de Broker et Webhooks Externes

## 1. Changer de Broker
Pour passer de Binance à un autre courtier, modifiez simplement `BROKER_TYPE` dans votre fichier `.env` :
```env
BROKER_TYPE=alpaca  # Actions US
# ou
BROKER_TYPE=paper_forex  # Forex simulé
```
Le bot charge automatiquement les instruments spécifiques configurés (`INSTRUMENTS_BINANCE`, `INSTRUMENTS_ALPACA`, etc.).

## 2. Serveur Webhook Intégré (TradingView, MT5, cTrader)
NexQuant intègre un serveur de webhook HTTP (`superbot/webhook/server.py`) écoutant sur le port `8080` pour exécuter des signaux en provenance d'autres plateformes.

### Exemple de configuration TradingView
Cochez **URL de Webhook** dans votre alerte TradingView (ex: via ngrok `https://abcd.ngrok-free.app/`) et envoyez le JSON suivant :
```json
{
  "symbol": "{{ticker}}",
  "action": "{{strategy.order.action}}",
  "price": {{close}},
  "source": "TradingView"
}
```

### Exemple de script MetaTrader 5 (MQL5)
```mql5
void SendSignalToNexQuant(string symbol, string action, double price) {
    string url = "https://votre-url-ngrok.ngrok-free.app/";
    string json = StringFormat("{\"symbol\": \"%s\", \"action\": \"%s\", \"price\": %.5f, \"source\": \"MT5\"}", symbol, action, price);
    char post[];
    char result[];
    string headers = "Content-Type: application/json\r\n";
    StringToCharArray(json, post);
    WebRequest("POST", url, headers, 5000, post, result, headers);
}
```
        



# ====================================================================
# LANGUAGE: ENGLISH
# ====================================================================


# 📖 Complete User Manual - SuperBot Unified Trading

## 1. Introduction
The **SuperBot Unified Trading** is an institutional-grade algorithmic trading system designed to run autonomously across multiple asset classes (Crypto, Stocks, Forex).
It combines multi-indicator technical analysis, a semantic NLP filter for raw trading rule ingestion, and a risk manager based on Kelly and Elder rules.

## 2. Prerequisites
- **Python**: Version 3.8 or higher (3.10 recommended).
- **Dependencies**: `pandas`, `numpy`, `requests`, `python-dotenv`.
- **Optional Dependencies**: `sentence-transformers` (for local NLP), `optuna` (for optimization).

## 3. Installation & Run
1. Clone or download the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your `.env` file in the project root.
4. Launch the bot:
   ```bash
   python superbot/main.py
   ```

## 4. Configuration (.env)
Key settings in the `.env` file:
- `BROKER_TYPE`: The active broker (`binance`, `alpaca`, `paper_forex`).
- `RISK_PCT`: Percentage of equity to risk per trade (default `1.0`%).
- `SCORE_MIN`: Minimum decision score (out of 10) to trigger a trade.
- `ENABLE_DASHBOARD`: Enable the web dashboard (`http://localhost:5000`).
        


# 📈 Expert Trader Guide - Advanced Logic

## 1. Core Philosophy: Instinct-Reason-Knowledge
The bot operates by merging three layers of analysis:
1. **Instinct**: Market sentiment processing (Fear & Greed, fundamental news).
2. **Reason**: Strict technical scoring based on 20+ indicators.
3. **Knowledge**: Semantic NLP ingestion of trading rules from financial literature (Ernest Chan, Alexander Elder, Bob Volman).

## 2. Performance Optimizations
To maximize responsiveness in volatile markets, key parameters have been fine-tuned:
- **Score threshold reduced** to `4` (from 6) to catch early market reversals.
- **ADX threshold** adjusted to `20` to detect trending market regimes faster.
- **Pyramiding** (`USE_PYRAMIDING=true`) enabled to scale into winning positions.
- **Volatility Filter** (`USE_VOLATILITY_FILTER=true`) requiring a minimum 0.5% volatility amplitude to prevent getting chopped in flat markets.
        


# 💻 Complete Technical Documentation

## 1. Modular Architecture
The system consists of independent modules coordinated by the central engine `superbot/main.py`:
- **Broker Adapter Layer** (`superbot/broker/`): Standardizes API connections for Binance, Alpaca, and the simulated Forex feed.
- **Risk Manager** (`superbot/risk/`): Manages overall exposure, leverage, and maximum drawdown limits.
- **Technical Indicators Engine** (`superbot/indicators/`): Performance-optimized O(N) calculations for indicators (EMA, RSI, MACD, Bollinger Bands, ATR, Supertrend).
- **Semantic Classifier** (`superbot/strategy/semantic_classifier.py`): NLP-driven rule parser using sentence embeddings.

## 2. Semantic NLP Classifier
The classifier loads extracted rules, generates embeddings using `sentence-transformers`, and evaluates cosine similarity against pre-defined action descriptions:
- `CAP_KELLY`: Caps the Kelly fraction to 0.125.
- `CAP_RISK_PCT`: Limits maximum risk per trade to 2%.
- `BONUS_SCORE_RANGING` / `BONUS_SCORE_TRENDING`: Dynamically boosts the score based on the detected market regime.

## 3. Bayesian Optimization (Optuna)
The `optimize_rules.py` script automatically adjusts weights and hyperparameters (like the min score threshold) by running rapid backtests and optimizing the Sharpe Ratio.
        


# 🔗 Broker & External Webhook Integration

## 1. Changing Brokers
To switch from Binance to another broker, modify `BROKER_TYPE` in your `.env` file:
```env
BROKER_TYPE=alpaca  # US Stocks
# or
BROKER_TYPE=paper_forex  # Simulated Forex
```
The bot dynamically loads the matching instruments (`INSTRUMENTS_BINANCE`, `INSTRUMENTS_ALPACA`, etc.).

## 2. Built-in Webhook Server (TradingView, MT5, cTrader)
NexQuant runs an HTTP webhook server (`superbot/webhook/server.py`) on port `8080` to listen for external signals.

### TradingView Setup
Check **Webhook URL** in your TradingView alert (e.g., pointing to your ngrok URL `https://abcd.ngrok-free.app/`) and send the following JSON:
```json
{
  "symbol": "{{ticker}}",
  "action": "{{strategy.order.action}}",
  "price": {{close}},
  "source": "TradingView"
}
```

### MetaTrader 5 (MQL5) Integration script
```mql5
void SendSignalToNexQuant(string symbol, string action, double price) {
    string url = "https://votre-url-ngrok.ngrok-free.app/";
    string json = StringFormat("{\"symbol\": \"%s\", \"action\": \"%s\", \"price\": %.5f, \"source\": \"MT5\"}", symbol, action, price);
    char post[];
    char result[];
    string headers = "Content-Type: application/json\r\n";
    StringToCharArray(json, post);
    WebRequest("POST", url, headers, 5000, post, result, headers);
}
```
        



# ====================================================================
# LANGUAGE: ESPAÑOL
# ====================================================================


# 📖 Manual de Usuario Completo - SuperBot Trading Unificado

## 1. Presentación
El **SuperBot Trading Unificado** es un sistema avanzado de trading algorítmico institucional diseñado para operar de forma autónoma en múltiples mercados (Criptomonedas, Acciones, Forex).
Combina análisis técnico multi-indicador, un filtro semántico NLP para asimilar reglas teóricas y un gestor de riesgos basado en las fórmulas de Kelly y Elder.

## 2. Requisitos del Sistema
- **Python**: Versión 3.8 o superior (se recomienda 3.10).
- **Dependencias**: `pandas`, `numpy`, `requests`, `python-dotenv`.
- **Dependencias opcionales**: `sentence-transformers` (NLP local), `optuna` (Optimización).

## 3. Instalación e Inicio
1. Descargue o clone el proyecto.
2. Instale los paquetes requeridos:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure su archivo `.env` en la raíz del proyecto.
4. Inicie el bot:
   ```bash
   python superbot/main.py
   ```

## 4. Configuration (.env)
Parámetros clave del archivo `.env`:
- `BROKER_TYPE`: El bróker activo (`binance`, `alpaca`, `paper_forex`).
- `RISK_PCT`: Porcentaje de capital en riesgo por operación (por defecto `1.0`%).
- `SCORE_MIN`: Puntuación mínima (sobre 10) requerida para abrir una posición.
- `ENABLE_DASHBOARD`: Activa el panel web interactivo (`http://localhost:5000`).
        


# 📈 Guía del Trader Experto - Lógica Avanzada

## 1. Filosofía Central: Instinto-Razón-Conocimiento
El bot funciona integrando tres capas de análisis:
1. **El Instinto**: Procesamiento del sentimiento de mercado (Fear & Greed, noticias).
2. **La Razón**: Puntuación técnica estricta basada en más de 20 indicadores.
3. **El Conocimiento**: Ingesta semántica mediante NLP de reglas de trading extraídas de libros financieros (Ernest Chan, Alexander Elder, Bob Volman).

## 2. Optimizaciones de Rendimiento y Reactividad
Para maximizar la reactividad en mercados altamente volátiles, se han optimizado varios parámetros:
- **Umbral de puntuación reducido** a `4` (en lugar de 6) para capturar giros tempranos.
- **Umbral del ADX** ajustado a `20` para detectar el inicio de tendencias con mayor rapidez.
- **Pyramiding** (`USE_PYRAMIDING=true`) activado para acumular posiciones a favor de tendencias fuertes.
- **Filtre de volatilidad** (`USE_VOLATILITY_FILTER=true`) que exige un rango mínimo del 0.5% para evitar operaciones en mercados laterales planos.
        


# 💻 Documentación Técnica Completa

## 1. Arquitectura Modular
El sistema está dividido en módulos independientes coordinados por el motor central `superbot/main.py`:
- **Broker Adapter Layer** (`superbot/broker/`): Estandariza las conexiones API a Binance, Alpaca y el simulador de Forex.
- **Risk Manager** (`superbot/risk/`): Controla la exposición total del portafolio y los límites de drawdown.
- **Technical Indicators Engine** (`superbot/indicators/`): Cálculos optimizados en O(N) para indicadores (EMA, RSI, MACD, Bandas de Bollinger, ATR, Supertrend).
- **Semantic Classifier** (`superbot/strategy/semantic_classifier.py`): Clasificador NLP mediante embeddings semánticos.

## 2. Clasificador Semántico NLP
El clasificador carga las reglas teóricas, genera sus embeddings utilizando `sentence-transformers` y evalúa la similitud de coseno contra descripciones de acción predefinidas:
- `CAP_KELLY`: Limita la fracción de Kelly a 0.125.
- `CAP_RISK_PCT`: Limita el riesgo máximo por operación al 2%.
- `BONUS_SCORE_RANGING` / `BONUS_SCORE_TRENDING`: Modifica dinámicamente la puntuación según el régimen de mercado.

## 3. Optimización Bayesiana (Optuna)
El script `optimize_rules.py` ajusta automáticamente los parámetros y pesos de las reglas mediante simulaciones de backtesting rápido para maximizar el Sharpe Ratio.
        


# 🔗 Cambio de Bróker y Webhooks Externos

## 1. Cambiar de Bróker
Para cambiar el bróker configurado, simplemente edite la variable `BROKER_TYPE` en su archivo `.env`:
```env
BROKER_TYPE=alpaca  # Acciones de EE.UU.
# o
BROKER_TYPE=paper_forex  # Forex Simulado
```
El bot cargará automáticamente los instrumentos específicos (`INSTRUMENTS_BINANCE`, `INSTRUMENTS_ALPACA`, etc.).

## 2. Servidor de Webhook Integrado (TradingView, MT5, cTrader)
NexQuant ejecuta un servidor HTTP de webhooks (`superbot/webhook/server.py`) en el puerto `8080` para recibir señales de trading externas.

### Configuración en TradingView
Active la opción **Webhook URL** en su alerta de TradingView (ej: usando ngrok `https://abcd.ngrok-free.app/`) y configure el siguiente mensaje JSON:
```json
{
  "symbol": "{{ticker}}",
  "action": "{{strategy.order.action}}",
  "price": {{close}},
  "source": "TradingView"
}
```

### Integración con MetaTrader 5 (MQL5)
```mql5
void SendSignalToNexQuant(string symbol, string action, double price) {
    string url = "https://votre-url-ngrok.ngrok-free.app/";
    string json = StringFormat("{\"symbol\": \"%s\", \"action\": \"%s\", \"price\": %.5f, \"source\": \"MT5\"}", symbol, action, price);
    char post[];
    char result[];
    string headers = "Content-Type: application/json\r\n";
    StringToCharArray(json, post);
    WebRequest("POST", url, headers, 5000, post, result, headers);
}
```
        

