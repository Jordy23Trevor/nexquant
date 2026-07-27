# NexQuant - Architecture Broker Flexible & Multi-Support

## 🎯 Vision: "Tout Broker, Une App"

**Objectif**: NexQuant supporte le broker de l'utilisateur (officiel ou générique) **OU** guide l'utilisateur vers un broker recommandé avec setup facile.

---

## 1. Stratégie Broker en Deux Phases

### Phase 1 (v1 - Stricte) : Brokers Officiellement Intégrés

```
BINANCE FUTURES
├─ Officiel support
├─ Testé en profondeur
├─ Risk management: leverage, min position size
├─ User base: Crypto traders, 24/7
└─ Status: ✅ Ready v1

ALPACA
├─ Officiel support
├─ Testé en profondeur
├─ Risk management: PDT rule, session hours
├─ User base: Stock traders, US only
└─ Status: ✅ Ready v1


AUTRES BROKERS (Interactive Brokers, TradeStation, etc)
├─ Non-officiels
├─ User peut essayer avec abstraction générique (v2+)
├─ NexQuant ne garantit pas stabilité
├─ Support limité
└─ Status: ⚠️ v2+ à expérimenter
```

### Phase 2 (v2+) : Support Générique via Abstraction

```
ARCHITECTURE:
  Broker-specific connectors (actuellement pour Binance/Alpaca)
           ↓
  Abstract Broker Interface (defini par NexQuant)
           ↓
  Generic Broker Adapter (pour tout broker avec REST API)
           ↓
  Risk Manager (règles génériques + overrides par broker)
           ↓
  Trading Engine (identique pour tous)
```

**Ce qu'on peut faire v2+:**
- Support Interactive Brokers (HTTP API)
- Support TradeStation (REST API)
- Support TD Ameritrade / Schwab (API)
- Support MetaTrader 5 (DDE / API indirect)
- Support OANDA Forex (API v20)

**Ce qu'on NE peut pas faire:**
- Brokers sans API (ex: certaines banques de détail)
- Brokers avec seulement FIX protocol (lourd, rarement utilisé retail)
- Brokers bloquant les bots tier-3 (ex: certains brokers asiatiques)

---

## 2. Onboarding Flow: Détection Broker & Validation

### Scenario A: User a déjà un broker & clés API

```
┌─ Step 1: Sélection Broker ─────────────────────────────────┐
│                                                              │
│  User: "Je trade sur [dropdown broker]"                     │
│                                                              │
│  Options:                                                   │
│  ┌─ OFFICIAL ─────────────┐  ┌─ EXPERIMENTAL ────────────┐ │
│  │ • Binance Futures      │  │ • Interactive Brokers      │ │
│  │ • Alpaca (US Stocks)   │  │ • TradeStation            │ │
│  │ • Paper Forex (Demo)   │  │ • OANDA                   │ │
│  │                         │  │ • Custom (advanced users) │ │
│  └─────────────────────────┘  └───────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌─ Step 2: Validation Broker Support ────────────────────────┐
│                                                              │
│  IF broker = BINANCE:                                       │
│    ✅ Officiel, fully supported                             │
│    ✅ All features available                                │
│    → Next: Enter API keys                                   │
│                                                              │
│  IF broker = ALPACA:                                        │
│    ✅ Officiel, fully supported                             │
│    ✅ All features available                                │
│    → Next: Enter API keys                                   │
│                                                              │
│  IF broker = INTERACTIVE_BROKERS:                           │
│    ⚠️  EXPERIMENTAL (support v2.1)                          │
│    ⚠️  Some features may not work                           │
│    ⚠️  Support limited to community forum                   │
│    ? User: "Continue anyway?" [Yes/No]                      │
│    → Next: Enter API credentials + Acknowledgement         │
│                                                              │
│  IF broker = UNKNOWN / CUSTOM:                             │
│    ⚠️  ADVANCED MODE                                        │
│    → Need: API base URL, auth method (API key, OAuth, etc)  │
│    → Need: Documentation link                               │
│    → Custom risk settings                                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌─ Step 3: API Key Input & Encryption ──────────────────────┐
│                                                              │
│  FOR BINANCE/ALPACA:                                        │
│    [Input API Key]                                          │
│    [Input Secret Key]                                       │
│    [Optional: Passphrase for some brokers]                  │
│    [Button: Get API keys (link to guide)]                   │
│                                                              │
│  FOR EXPERIMENTAL BROKERS:                                  │
│    [Input API Key]                                          │
│    [Input API Secret]                                       │
│    [Select Auth method: Basic/Bearer/Custom Header]         │
│    [Input Auth Header Name (optional)]                      │
│                                                              │
│  FOR CUSTOM BROKERS:                                        │
│    [Input API Endpoint URL]                                 │
│    [Input Auth Method dropdown]                             │
│    [Input Credentials based on method]                      │
│    [Test connection button]                                 │
│                                                              │
│  ACTION: On input → Encrypt (AES-256) → Verify hash        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌─ Step 4: Connection Test ──────────────────────────────────┐
│                                                              │
│  OFFICIAL BROKERS (Binance, Alpaca):                        │
│    ✅ Call /account endpoint                                │
│    ✅ Verify API key valid                                  │
│    ✅ Fetch account info (equity, currency)                 │
│    ✅ Check minimum capital requirement                     │
│      └─ Binance: min $500                                   │
│      └─ Alpaca: min $25,000 (PDT)                           │
│      └─ Others: check or skip                               │
│                                                              │
│  EXPERIMENTAL/CUSTOM BROKERS:                               │
│    ⚠️  Attempt connection                                   │
│    ⚠️  If fails → show error + troubleshoot guide           │
│    ⚠️  If succeeds → warn user "Limited support"            │
│    ⚠️  Detect: account balance, base currency               │
│                                                              │
│  IF TEST FAILS:                                             │
│    ❌ Show specific error:                                  │
│       "Invalid API Key"                                     │
│       "API endpoint not responding"                         │
│       "Insufficient permissions"                            │
│    → Link to troubleshoot guide                             │
│    → Option to retry                                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌─ Step 5: Broker Setup Complete ────────────────────────────┐
│                                                              │
│  ✅ API key saved (encrypted)                               │
│  ✅ Account info cached                                     │
│  ✅ Broker type recorded                                    │
│  ✅ Risk limits set (based on account size)                 │
│  ✅ Supported features determined                           │
│                                                              │
│  DASHBOARD shows:                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Broker: Binance Futures (Official ✅)              │   │
│  │ Account Balance: $5,000 USDT                        │   │
│  │ Status: Connected ✅                                │   │
│  │ Features: All strategies available                  │   │
│  │ Risk Limit: 2% per trade, $100/day max loss         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Scenario B: User n'a pas de broker

```
┌─ Step 1: "You don't have a broker yet?" ───────────────┐
│                                                          │
│  ⚠️  NexQuant needs a broker to execute trades          │
│                                                          │
│  We recommend:                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 🏆 BINANCE FUTURES                             │   │
│  │    • 24/7 trading                              │   │
│  │    • Low fees (0.02% - 0.04%)                  │   │
│  │    • Min capital: $500                         │   │
│  │    • ✅ Fully supported by NexQuant             │   │
│  │    [Create Account] → Guided setup              │   │
│  │                                                 │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ 📈 ALPACA (US Stocks Only)                     │   │
│  │    • Commission-free stocks                    │   │
│  │    • Session-based (9:30-16:00 ET)             │   │
│  │    • Min capital: $25,000 (PDT)                │   │
│  │    • ✅ Fully supported by NexQuant             │   │
│  │    [Create Account] → Guided setup              │   │
│  │                                                 │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ 🎮 PAPER TRADING (Demo, No Real Money)         │   │
│  │    • Simulate trades                           │   │
│  │    • Test strategies risk-free                 │   │
│  │    • ✅ Available now                           │   │
│  │    [Start Paper Trading] → Immediate            │   │
│  │                                                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Or: Already have other broker?                         │
│  [Enter your own broker] → Advanced setup               │
│                                                          │
└──────────────────────────────────────────────────────────┘
                            ↓
         [IF CHOOSES BINANCE/ALPACA]
                            ↓
┌─ Step 2: Broker Setup Guide ──────────────────────────┐
│                                                          │
│  🔗 Video Tutorial (5 min): "Get Binance API Keys"      │
│  📖 Written Guide: Step-by-step with screenshots       │
│                                                          │
│  1. Sign up on [broker website]                         │
│  2. Go to API Management                               │
│  3. Create API key                                     │
│  4. Enable Trading Permission                          │
│  5. Copy API Key & Secret                              │
│  6. Paste into NexQuant (we'll encrypt it)              │
│                                                          │
│  [Copy Binance Setup Link] [Continue]                   │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Architecture Abstraction Broker

### 3.1 Current: Broker-Specific Connectors (v1)

```python
# Current architecture (Binance & Alpaca specific)

from brokers.binance_connector import BinanceConnector
from brokers.alpaca_connector import AlpacaConnector
from brokers.paper_forex_connector import PaperForexConnector

class BrokerFactory:
    """Selects right connector based on broker type"""
    
    @staticmethod
    def create(broker_type: str, api_key: str, api_secret: str) -> BrokerConnector:
        if broker_type == "binance":
            return BinanceConnector(api_key, api_secret)
        elif broker_type == "alpaca":
            return AlpacaConnector(api_key, api_secret)
        elif broker_type == "paper_forex":
            return PaperForexConnector()
        else:
            raise ValueError(f"Broker {broker_type} not supported")

# Usage
broker = BrokerFactory.create("binance", api_key, api_secret)
positions = broker.get_positions()  # Returns standardized data
```

### 3.2 Future: Generic Abstraction Layer (v2+)

```python
# Abstraction interface (works for ANY broker)

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class Position:
    """Standard position format (normalized across brokers)"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_pct: float
    broker_id: str

@dataclass
class Order:
    """Standard order format"""
    order_id: str
    symbol: str
    quantity: float
    price: float
    side: str  # BUY or SELL
    order_type: str  # MARKET, LIMIT, STOP_LIMIT
    status: str  # PENDING, OPEN, FILLED, CANCELLED
    created_at: datetime
    filled_at: datetime = None

class AbstractBrokerConnector(ABC):
    """Base interface for any broker connector"""
    
    def __init__(self, broker_type: str, credentials: Dict[str, str]):
        self.broker_type = broker_type
        self.credentials = credentials
        self.session = None
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Verify API credentials are valid"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Return: {balance, currency, leverage, equity}"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Return standardized list of positions"""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, quantity: float, side: str, 
                   order_type: str, price: float = None, 
                   stop_loss: float = None, take_profit: float = None) -> Order:
        """Place order, return standardized Order object"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Order:
        """Get status of existing order"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel open order"""
        pass
    
    @abstractmethod
    def close_position(self, symbol: str) -> bool:
        """Close existing position"""
        pass
    
    @abstractmethod
    def get_recent_trades(self, limit: int = 100) -> List[Trade]:
        """Get closed trades history"""
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return: {status, latency_ms, timestamp}"""
        pass

# Concrete implementations

class BinanceConnector(AbstractBrokerConnector):
    """Specific implementation for Binance"""
    
    def authenticate(self) -> bool:
        # Binance-specific auth
        response = self._request("GET", "/fapi/v1/account")
        return response.status_code == 200
    
    def get_positions(self) -> List[Position]:
        # Binance API returns positions differently
        # Convert to standard Position format
        raw_positions = self._request("GET", "/fapi/v1/openOrders").json()
        return [Position(
            symbol=p["symbol"],
            quantity=float(p["quantity"]),
            entry_price=float(p["avgPrice"]),
            # ... normalize all fields
        ) for p in raw_positions]
    
    def place_order(self, symbol: str, quantity: float, side: str, ...) -> Order:
        # Binance-specific order placement
        payload = {
            "symbol": symbol,
            "side": side.upper(),
            "quantity": quantity,
            # Binance uses different field names
        }
        response = self._request("POST", "/fapi/v1/order", data=payload)
        # Convert Binance response → standard Order format
        return self._convert_order_response(response.json())

class AlpacaConnector(AbstractBrokerConnector):
    """Specific implementation for Alpaca"""
    # Similar pattern: convert Alpaca API to standard format

class InteractiveBrokersConnector(AbstractBrokerConnector):
    """Generic support for Interactive Brokers (v2+)"""
    # IB API is different but follows same abstraction

class CustomBrokerConnector(AbstractBrokerConnector):
    """Generic connector for any REST-based broker (v2+)"""
    
    def __init__(self, broker_type: str, credentials: Dict, 
                 config: BrokerConfig):
        super().__init__(broker_type, credentials)
        self.config = config  # Contains: endpoint_url, auth_method, etc
    
    def authenticate(self) -> bool:
        # Generic HTTP request based on config
        response = self._make_request(
            method=self.config.auth_endpoint_method,
            url=self.config.auth_endpoint_url,
            auth_type=self.config.auth_type,  # "Bearer", "API-Key", "Basic"
            credentials=self.credentials
        )
        return response.status_code == 200
    
    def get_positions(self) -> List[Position]:
        # Call generic endpoint, parse response
        raw_data = self._make_request(
            method="GET",
            url=self.config.positions_endpoint
        ).json()
        # Map generic format to standard Position
        return self._parse_positions(raw_data, self.config.position_mapping)
    
    def place_order(self, symbol: str, quantity: float, ...) -> Order:
        # Build request based on broker's API spec
        payload = self.config.build_order_payload(
            symbol=symbol, quantity=quantity, ...
        )
        response = self._make_request(
            method="POST",
            url=self.config.order_endpoint,
            data=payload
        )
        return self._parse_order_response(response.json(), self.config)

# Usage is identical regardless of broker:

broker = BrokerFactory.create(
    broker_type="binance",  # or "alpaca", "interactive_brokers", "custom"
    api_key="xxx",
    api_secret="yyy"
)

positions = broker.get_positions()  # Returns List[Position] - SAME FORMAT
order = broker.place_order("BTC/USDT", 1.0, "BUY", "MARKET")  # Returns Order - SAME FORMAT
```

### 3.3 Generic Broker Configuration (v2+)

```python
# Schema for describing any broker's API

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

class AuthMethod(Enum):
    API_KEY = "api_key"  # Separate key + secret headers
    BEARER_TOKEN = "bearer"  # Authorization: Bearer token
    BASIC_AUTH = "basic"  # Basic auth (username:password)
    CUSTOM_HEADER = "custom"  # Custom auth header

@dataclass
class BrokerConfig:
    """Describes how NexQuant connects to any broker"""
    
    # Broker identity
    broker_id: str  # "binance", "interactive_brokers", "custom_xxx"
    name: str  # "Binance Futures", "Interactive Brokers"
    broker_url: str  # "https://www.binance.com"
    
    # API endpoint configuration
    api_base_url: str  # "https://fapi.binance.com"
    
    # Authentication
    auth_method: AuthMethod
    auth_header_key: Optional[str] = None  # e.g., "X-API-Key"
    auth_header_secret: Optional[str] = None  # e.g., "X-API-Secret"
    
    # Endpoints mapping (where to call for each action)
    endpoints: Dict[str, str] = {
        "account": "/v1/account",
        "positions": "/v1/positions",
        "orders": "/v1/orders",
        "trades": "/v1/trades",
        "health": "/v1/health",
    }
    
    # Field mappings (how to parse responses)
    response_mapping: Dict[str, str] = {
        "position.symbol": "instrument",
        "position.quantity": "size",
        "position.entry_price": "avgPrice",
        "order.order_id": "orderId",
        "order.status": "orderStatus",
    }
    
    # Order type support
    supported_order_types: List[str] = ["MARKET", "LIMIT", "STOP_LIMIT"]
    
    # Position management
    supports_bracket_orders: bool = False  # Can place TP + SL in one call?
    supports_stop_loss: bool = True
    supports_take_profit: bool = True
    
    # Risk & limits
    min_order_size: Dict[str, float] = {"BTC/USDT": 0.001}
    max_leverage: float = 1.0  # No leverage by default
    base_currency: str = "USD"
    
    # Trading hours (if applicable)
    trading_hours: Optional[str] = "24/7"  # or "09:30-16:00 ET"
    
    # Rate limiting
    rate_limit_requests: int = 1200
    rate_limit_period_seconds: int = 60
    
    # Fees
    maker_fee: float = 0.001  # 0.1%
    taker_fee: float = 0.001

# Database: Store broker configs for all supported brokers
class BrokerConfigs:
    BINANCE = BrokerConfig(
        broker_id="binance",
        name="Binance Futures",
        api_base_url="https://fapi.binance.com",
        auth_method=AuthMethod.API_KEY,
        auth_header_key="X-MBX-APIKEY",
        endpoints={
            "account": "/fapi/v1/account",
            "positions": "/fapi/v1/openOrders",
            "orders": "/fapi/v1/allOrders",
            ...
        },
        response_mapping={
            "position.symbol": "symbol",
            "position.quantity": "origQty",
            ...
        },
        supported_order_types=["MARKET", "LIMIT", "STOP", "TAKE_PROFIT"],
        supports_bracket_orders=False,
        max_leverage=125,
        trading_hours="24/7",
    )
    
    ALPACA = BrokerConfig(
        broker_id="alpaca",
        name="Alpaca",
        api_base_url="https://api.alpaca.markets",
        auth_method=AuthMethod.BEARER_TOKEN,
        endpoints={
            "account": "/v2/account",
            "positions": "/v2/positions",
            ...
        },
        response_mapping={
            "position.symbol": "symbol",
            "position.quantity": "qty",
            ...
        },
        supported_order_types=["market", "limit"],
        supports_bracket_orders=True,
        max_leverage=4,
        trading_hours="09:30-16:00 ET",
    )
    
    # Custom broker (user-defined)
    CUSTOM = BrokerConfig(
        broker_id="custom",
        name="User Custom Broker",
        api_base_url="",  # User provides
        auth_method=AuthMethod.CUSTOM_HEADER,  # User selects
        # ... other fields configurable by user
    )
```

### 3.4 Risk Management Adapter (Broker-Aware)

```python
# Risk rules vary by broker → abstraction handles it

class BrokerRiskManager:
    """Applies broker-specific risk rules"""
    
    def __init__(self, broker_config: BrokerConfig, account_info: Dict):
        self.config = broker_config
        self.account_equity = account_info["equity"]
        self.account_currency = account_info["currency"]
    
    def validate_position_size(self, symbol: str, quantity: float, 
                               entry_price: float, risk_pct: float = 0.02) -> bool:
        """Check if position size is valid for this broker"""
        
        # 1. Check minimum position size (broker-specific)
        min_size = self.config.min_order_size.get(symbol, 0.001)
        if quantity < min_size:
            raise ValueError(f"Position {quantity} below minimum {min_size}")
        
        # 2. Check leverage limits
        notional_value = quantity * entry_price
        max_notional = self.account_equity * self.config.max_leverage
        if notional_value > max_notional:
            raise ValueError(f"Exceeds max leverage for {self.config.name}")
        
        # 3. Risk check (same for all brokers)
        risk_amount = self.account_equity * risk_pct
        # ... rest of validation
        
        return True
    
    def adjust_for_broker(self, order_params: Dict) -> Dict:
        """Convert generic order params to broker-specific format"""
        
        if self.config.broker_id == "binance":
            # Binance needs different field names
            return {
                "symbol": order_params["symbol"],
                "side": order_params["side"].upper(),
                "type": "MARKET" if order_params["order_type"] == "MARKET" else "LIMIT",
                # Binance doesn't support bracket orders natively
                # So we place separate SL/TP orders
            }
        
        elif self.config.broker_id == "alpaca":
            # Alpaca supports bracket orders
            return {
                "symbol": order_params["symbol"],
                "qty": order_params["quantity"],
                "side": order_params["side"].lower(),
                "type": order_params["order_type"].lower(),
                "order_class": "bracket",  # Alpaca feature
                "take_profit": {"limit_price": order_params["take_profit"]},
                "stop_loss": {"stop_price": order_params["stop_loss"]},
            }
        
        elif self.config.supports_bracket_orders:
            # Generic broker with bracket support
            return self._generic_bracket_order(order_params)
        
        else:
            # Fallback: place orders separately
            return self._separate_orders(order_params)
```

---

## 4. Database Schema: Multi-Broker Support

```sql
-- Store supported brokers (static configuration)
CREATE TABLE broker_types (
  id SERIAL PRIMARY KEY,
  broker_id VARCHAR(50) UNIQUE,  -- "binance", "alpaca", "ib", "custom"
  name VARCHAR(100),
  url VARCHAR(255),
  api_base_url VARCHAR(255),
  status VARCHAR(20),  -- "official", "experimental", "custom"
  official_support BOOLEAN,
  official_support_version VARCHAR(10),  -- "1.0", "2.1", "beta"
  documentation_url TEXT,
  created_at TIMESTAMP
);

-- Store user's broker connections (dynamic)
CREATE TABLE user_broker_connections (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  broker_type_id INT REFERENCES broker_types(id),
  
  -- API credentials (encrypted)
  encrypted_api_key BYTEA,
  encrypted_api_secret BYTEA,
  encrypted_passphrase BYTEA,
  
  -- Custom configuration (for experimental/generic brokers)
  custom_api_endpoint VARCHAR(255),  -- For custom brokers
  custom_auth_method VARCHAR(50),  -- "api_key", "bearer", "basic", "custom"
  custom_auth_header_name VARCHAR(100),  -- "X-API-Key", "Authorization", etc
  
  -- Connection metadata
  account_currency VARCHAR(10),  -- "USD", "USDT", "EUR"
  account_balance DECIMAL(20, 8),
  account_leverage DECIMAL(5, 2),
  is_live BOOLEAN,  -- TRUE = real money, FALSE = paper/demo
  
  -- Status
  status VARCHAR(20),  -- "connected", "disconnected", "error", "expired"
  last_connection_check TIMESTAMP,
  last_error_message TEXT,
  
  -- Support level
  support_level VARCHAR(20),  -- "official", "experimental", "unsupported"
  features_available JSON,  -- {"paper_trading": true, "strategies": ["trend_follow"], ...}
  
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

-- Broker feature matrix (which features work with which brokers)
CREATE TABLE broker_feature_matrix (
  id SERIAL PRIMARY KEY,
  broker_type_id INT REFERENCES broker_types(id),
  feature_name VARCHAR(100),  -- "bracket_orders", "paper_trading", "webhooks"
  is_supported BOOLEAN,
  notes TEXT,
  created_at TIMESTAMP
);

-- Broker health logs (track API reliability)
CREATE TABLE broker_health_logs (
  id UUID PRIMARY KEY,
  broker_type_id INT REFERENCES broker_types(id),
  timestamp TIMESTAMP,
  status VARCHAR(20),  -- "healthy", "degraded", "down"
  latency_ms INT,
  error_count INT,
  success_count INT,
  uptime_pct DECIMAL(5, 2),
  created_at TIMESTAMP
);

-- Example queries:

-- List all brokers and their support level
SELECT broker_types.name, broker_types.status, COUNT(user_broker_connections.id) as user_count
FROM broker_types
LEFT JOIN user_broker_connections ON broker_types.id = user_broker_connections.broker_type_id
GROUP BY broker_types.id;

-- Get user's connected brokers
SELECT bt.name, ubc.status, ubc.account_balance, ubc.is_live
FROM user_broker_connections ubc
JOIN broker_types bt ON ubc.broker_type_id = bt.id
WHERE ubc.user_id = 'user_123';

-- Check if a feature is available for a user's broker
SELECT bfm.is_supported
FROM broker_feature_matrix bfm
JOIN user_broker_connections ubc ON bfm.broker_type_id = ubc.broker_type_id
WHERE ubc.user_id = 'user_123'
  AND ubc.broker_type_id = 1
  AND bfm.feature_name = 'bracket_orders';
```

---

## 5. API Endpoints: Broker Management

```
BROKER DETECTION & LISTING
  GET /api/v1/brokers/available
    Returns: All supported brokers (official + experimental)
    Response: [{
      "id": "binance",
      "name": "Binance Futures",
      "status": "official",
      "support_level": "fully_supported",
      "min_capital": 500,
      "trading_hours": "24/7",
      "features": ["paper_trading", "strategies", "webhooks"]
    }]

BROKER CONNECTION MANAGEMENT
  POST /api/v1/brokers/connect
    Input: {
      "broker_type": "binance",
      "api_key": "...",
      "api_secret": "...",
      "is_live": true
    }
    Returns: Connection ID, validation status
    
  POST /api/v1/brokers/{connection_id}/test
    Input: (none)
    Returns: {
      "status": "success",
      "account_balance": 5000,
      "currency": "USDT",
      "connection_latency_ms": 145
    }
  
  GET /api/v1/brokers/my-connections
    Returns: List of user's broker connections
    Response: [{
      "connection_id": "conn_123",
      "broker": "binance",
      "status": "connected",
      "balance": 5000,
      "last_health_check": "2026-06-27T10:30:00Z",
      "features_available": ["paper_trading", "webhook"]
    }]
  
  DELETE /api/v1/brokers/{connection_id}
    Disconnects broker, revokes API keys

BROKER HEALTH MONITORING
  GET /api/v1/brokers/health
    Returns: Real-time status of all brokers
    Response: [{
      "broker": "binance",
      "status": "healthy",
      "latency_ms": 45,
      "uptime_pct": 99.9,
      "last_check": "2026-06-27T10:35:00Z"
    }]

GENERIC BROKER SETUP (v2+)
  POST /api/v1/brokers/custom/connect
    Input: {
      "broker_name": "My Custom Broker",
      "api_endpoint": "https://api.mybroker.com",
      "auth_method": "api_key",
      "auth_header_name": "X-API-Key",
      "api_key": "...",
      "api_secret": "...",
      "account_currency": "USD"
    }
    Returns: Connection details + feature detection
    
  POST /api/v1/brokers/custom/{connection_id}/test-endpoint
    Input: {
      "method": "GET",
      "path": "/v1/account",
      "expected_response_format": "json"
    }
    Returns: Response preview + field mapping assistance
```

---

## 6. UI/UX Flow: Multi-Broker Onboarding

### Screen 1: Broker Selection
```
┌─ NexQuant Broker Setup ──────────────────────┐
│                                              │
│  📊 Connect Your Trading Broker               │
│                                              │
│  Do you already have a broker & API keys?   │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │ ✅ Yes, I have a broker                │ │
│  └────────────────────────────────────────┘ │
│          → Go to step 2 (select broker)     │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │ ❌ No, I need to sign up                │ │
│  └────────────────────────────────────────┘ │
│          → Go to step 3 (recommendations)   │
│                                              │
└──────────────────────────────────────────────┘
```

### Screen 2: Broker Selection Dropdown
```
┌─ Select Your Broker ─────────────────────────┐
│                                              │
│  🔹 Which broker do you use?                 │
│                                              │
│  ┌─ MOST POPULAR ──────────────────────────┐│
│  │ ◉ Binance Futures                       ││
│  │    ✅ Fully supported                    ││
│  │    • 24/7 trading, low fees              ││
│  │    • Min capital: $500                   ││
│  │    [Setup Guide →]                       ││
│  └─────────────────────────────────────────┘│
│                                              │
│  ┌─ OTHER SUPPORTED ───────────────────────┐│
│  │ ◯ Alpaca                                ││
│  │    ✅ Fully supported (US stocks only)   ││
│  │    • Min capital: $25,000                ││
│  │    [Setup Guide →]                       ││
│  │                                          ││
│  │ ◯ Paper Forex (Demo)                   ││
│  │    ✅ Fully supported (no real money)    ││
│  │    [Start Paper Trading →]               ││
│  └─────────────────────────────────────────┘│
│                                              │
│  ┌─ EXPERIMENTAL ──────────────────────────┐│
│  │ ◯ Interactive Brokers                  ││
│  │    ⚠️  Limited support (community)       ││
│  │ ◯ TradeStation                          ││
│  │    ⚠️  Limited support (beta)            ││
│  │ ◯ OANDA                                 ││
│  │    ⚠️  Limited support (beta)            ││
│  └─────────────────────────────────────────┘│
│                                              │
│  ┌─ ADVANCED ──────────────────────────────┐│
│  │ ◯ Other broker (custom API setup)      ││
│  │    ⚠️  Advanced mode                     ││
│  │ [Learn more about custom brokers →]     ││
│  └─────────────────────────────────────────┘│
│                                              │
│           [Continue] [Skip for now]          │
│                                              │
└──────────────────────────────────────────────┘
```

### Screen 3: API Key Input (Specific to Broker)

**For Binance/Alpaca (Official):**
```
┌─ Enter Your API Keys ───────────────────────┐
│                                              │
│  🔐 Your API keys are encrypted and stored  │
│     securely. NexQuant can only READ.       │
│                                              │
│  Binance API Key                             │
│  ┌────────────────────────────────────────┐ │
│  │                                        │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  Binance Secret Key                          │
│  ┌────────────────────────────────────────┐ │
│  │ ••••••••••••••••••••••                 │ │ (masked)
│  └────────────────────────────────────────┘ │
│                                              │
│  📖 [How to get Binance API keys]            │
│  🎬 [Video tutorial (3 min)]                 │
│                                              │
│           [Test Connection] [Connect]        │
│                                              │
└──────────────────────────────────────────────┘
```

**For Experimental Brokers:**
```
┌─ Interactive Brokers Setup ──────────────────┐
│                                              │
│  ⚠️  LIMITED SUPPORT - Community Help Only  │
│                                              │
│  This broker is not officially supported    │
│  by NexQuant. You may experience issues.    │
│  [Learn more about limitations →]           │
│                                              │
│  Continue? [Yes, proceed] [Choose different]│
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │ API Key                                │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │ API Secret                             │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  [Test Connection] [Connect]                 │
│                                              │
└──────────────────────────────────────────────┘
```

**For Custom Brokers:**
```
┌─ Custom Broker Setup (Advanced) ────────────┐
│                                              │
│  This mode requires technical knowledge     │
│  of your broker's REST API.                 │
│                                              │
│  Broker Name                                 │
│  ┌────────────────────────────────────────┐ │
│  │ My Trading Platform                    │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  API Base URL                                │
│  ┌────────────────────────────────────────┐ │
│  │ https://api.mybroker.com               │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  Authentication Method                       │
│  ┌─ Dropdown ──────────────────────────────┐│
│  │ API Key (separate key + secret)    ▼  ││
│  └─────────────────────────────────────────┘│
│                                              │
│  API Key Header Name (optional)              │
│  ┌────────────────────────────────────────┐ │
│  │ X-API-Key                              │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  API Key                                     │
│  ┌────────────────────────────────────────┐ │
│  │                                        │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  API Secret                                  │
│  ┌────────────────────────────────────────┐ │
│  │                                        │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  [Test Connection] [Advanced Options]        │
│                                              │
└──────────────────────────────────────────────┘
```

---

## 7. Implementation Roadmap

### Phase 1 (v1.0 - Weeks 1-12): Official Brokers Only
```
✅ Binance Futures (full integration)
✅ Alpaca (full integration)
✅ Paper Forex (built-in simulator)
❌ Custom brokers (not supported)
❌ Generic connectors (not implemented)

Scope: Simple broker selection, API key input, full feature support
```

### Phase 2 (v2.0 - Weeks 13-24): Experimental Brokers

```
✅ Abstract broker interface implemented
✅ Interactive Brokers connector (generic adapter)
✅ TradeStation connector (generic adapter)
✅ OANDA Forex connector
❌ Full feature support (some features may not work)
⚠️  Community support only (not official)

Scope: Allow experimental brokers with warnings, community troubleshooting
```

### Phase 3 (v2.1+): Generic Custom Broker Support

```
✅ Generic REST API adapter
✅ User-configurable broker setup
✅ Endpoint mapping UI
✅ Custom broker feature detection

Scope: Any broker with REST API can theoretically work
Risk: High support burden, unpredictable compatibility
```

---

## 8. Risk & Limitations by Broker Type

### Official Brokers (v1)

| Aspect | Binance | Alpaca | Paper Forex |
|--------|---------|--------|-------------|
| **Support Level** | ✅ Full | ✅ Full | ✅ Full |
| **Feature Coverage** | 100% | 100% | 100% |
| **SLA** | 99.5% uptime | 99.9% uptime | 100% (local) |
| **Risk Level** | Low | Low | None (demo) |
| **User Support** | Email + chat | Email + chat | Email + chat |
| **Documented Edge Cases** | Yes | Yes | Yes |

### Experimental Brokers (v2+)

| Aspect | Interactive Brokers | TradeStation | OANDA |
|--------|-------------------|--------------|-------|
| **Support Level** | ⚠️ Limited | ⚠️ Limited | ⚠️ Limited |
| **Feature Coverage** | ~70% | ~70% | ~50% |
| **Tested By** | Community | Community | Community |
| **Response Time** | Slow (24-48h) | Slow (24-48h) | Slow (24-48h) |
| **Known Issues** | Multiple | Multiple | Multiple |
| **Recommendation** | Advanced users only | Advanced users only | Forex-only users |

### Custom/Generic Brokers (v3+)

| Aspect | Rating |
|--------|--------|
| **Support Level** | ❌ None (at user's own risk) |
| **Feature Coverage** | Unknown (depends on API) |
| **Reliability** | Depends on broker's API quality |
| **Documentation Required** | User must provide API docs |
| **NexQuant Liability** | Disclaimer: "Use at own risk" |
| **Recommendation** | Extremely advanced users only |

---

## 9. Onboarding Copy for Different Brokers

### Official Brokers (Reassuring)
```
✅ Binance Futures
   "Fully supported and tested by NexQuant.
    Full access to all strategies and features.
    Direct support available."
```

### Experimental Brokers (Cautious)
```
⚠️ Interactive Brokers
   "Community support available.
    Some features may not work as expected.
    Not officially tested by NexQuant team.
    [Learn more about limitations]"
```

### Custom Brokers (Disclaimer)
```
❌ Custom Broker
   "ADVANCED MODE - Use at your own risk.
    No support from NexQuant.
    You're responsible for API configuration.
    [I understand the risks]"
```

---

## 10. Example User Journey: Custom Broker

```
User Profile: "I use Dukascopy (Forex broker), want NexQuant automation"

Step 1: User selects "Other broker (custom API setup)"
Step 2: User enters:
  - Broker name: "Dukascopy"
  - API endpoint: "https://api.dukascopy.com/v1"
  - Auth method: "Bearer Token"
  - Bearer token: "xyz123..."
Step 3: System tries connection:
  - GET https://api.dukascopy.com/v1/account
  - ❌ Fails: "401 Unauthorized"
Step 4: User tries again, checks documentation
  - Realizes need custom header "Authorization-Token"
  - Updates config
Step 5: Connection succeeds
  - System auto-detects: {account_balance: 10000, currency: "USD"}
  - Determines available features: {paper_trading: false, webhooks: false, ...}
Step 6: Dashboard shows:
  ┌────────────────────────────────┐
  │ Broker: Dukascopy (Custom)     │
  │ Status: ⚠️ Connected (Experimental) │
  │ Features: Limited               │
  │ Support: Community forum only   │
  │ [Docs] [Report Issue]           │
  └────────────────────────────────┘

User understands: "This isn't official support, use at own risk"
NexQuant protects: "Clear disclaimer = lower liability"
```

---

## Conclusion

**C'est possible à 100%, mais par étapes :**

✅ **v1 (Weeks 1-12)**: Binance, Alpaca, Paper Forex = production-ready
✅ **v2 (Weeks 13-24)**: Generic abstraction layer + experimental brokers
✅ **v3 (Weeks 25+)**: Custom broker setup for advanced users

**Key principles:**
1. **Official brokers first** = stability, support, liability protection
2. **Experimental brokers second** = expand reach, community support
3. **Generic brokers third** = max flexibility, minimal support

**Risk mitigation:**
- Clear disclaimers for experimental brokers
- Feature detection (what works, what doesn't)
- Fallback to paper trading if live trading unavailable
- Community forum for troubleshooting
- Legal: "Use at your own risk" for custom brokers

**User experience:**
- Simple dropdown for official brokers
- Warnings for experimental brokers
- Technical setup UI for custom brokers
- Same dashboard/features once connected (abstraction handles differences)

**Monétisation:**
- Starter tier: Official brokers only
- Pro tier: Experimental brokers included
- Professional tier: Custom brokers + dedicated support
