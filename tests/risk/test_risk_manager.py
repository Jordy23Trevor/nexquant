import pytest
from superbot.risk.risk_manager import RiskManager

@pytest.fixture
def risk_manager():
    # Configuration minimale factice
    config = {
        'RISK_PCT': 2.0,
        'MAX_OPEN_POSITIONS': 5,
        'MAX_DAILY_LOSS_PCT': 5.0,
        'KELLY_FRACTION': 0.5,
        'MIN_TRADES_FOR_KELLY': 50,
        'COMMISSION_PCT': 0.1,
        'SLIPPAGE_PCT': 0.05
    }
    return RiskManager(config)

def test_calculate_position_size_zero_balance(risk_manager):
    # Solde de compte nul
    size, details = risk_manager.calculate_position_size(
        account_balance=0.0,
        entry_price=50000.0,
        stop_loss=49000.0,
        symbol="BTC/USDT"
    )
    assert size == 0.0

def test_calculate_position_size_negative_balance(risk_manager):
    # Solde négatif
    size, details = risk_manager.calculate_position_size(
        account_balance=-100.0,
        entry_price=50000.0,
        stop_loss=49000.0,
        symbol="BTC/USDT"
    )
    assert size == 0.0

def test_calculate_position_size_zero_risk(risk_manager):
    # ATR = 0 ou Stop loss égal au prix d'entrée (risque de 0 sur le prix brut)
    # Note: Le coût de transaction va rajouter un petit risque
    size, details = risk_manager.calculate_position_size(
        account_balance=10000.0,
        entry_price=50000.0,
        stop_loss=50000.0,
        symbol="BTC/USDT"
    )
    assert size > 0.0 # Un léger risque subsiste via les frais

def test_kelly_criterion_insufficient_history(risk_manager):
    # Avec un historique insuffisant, Kelly ne doit pas impacter
    risk_manager.trade_history = [{"pnl": 10} for _ in range(10)] # Seulement 10 trades < 50
    size, details = risk_manager.calculate_position_size(
        account_balance=10000.0,
        entry_price=1.1000,
        stop_loss=1.0900,
        symbol="EUR/USD"
    )
    assert size > 0.0

def test_get_risk_metrics(risk_manager):
    metrics = risk_manager.get_risk_metrics(10000.0)
    assert isinstance(metrics, dict)
    assert 'drawdown_pct' in metrics
    assert 'win_rate' in metrics
    assert 'profit_factor' in metrics


def test_record_trade_consecutive_losses_are_atomic(risk_manager, monkeypatch, tmp_path):
    """
    200 clôtures perdantes concurrentes doivent donner exactement 200 pertes
    consécutives : sans le verrou interne, le read-modify-write de
    consecutive_losses[symbol] perdrait des incréments.
    """
    from concurrent.futures import ThreadPoolExecutor

    monkeypatch.setattr("superbot.config.TRADE_LOG_FILE", str(tmp_path / "trades.jsonl"))

    n = 200

    def _record(_):
        risk_manager.record_trade({
            'symbol': 'BTC/USDT', 'status': 'closed', 'pnl': -1.0,
            'timestamp': '2026-01-01T00:00:00',
        })

    with ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(_record, range(n)))

    assert risk_manager.consecutive_losses.get('BTC/USDT', 0) == n
    assert len(risk_manager.trade_history) == min(n, 100)
