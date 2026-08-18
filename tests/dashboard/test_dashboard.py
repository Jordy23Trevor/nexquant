"""Régressions du dashboard legacy (port 5000)."""

from http.server import ThreadingHTTPServer

from superbot.dashboard.dashboard import (
    DashboardServer,
    _is_displayable_closed_trade,
)


def test_ghost_cleanup_is_not_a_closed_trade():
    ghost = {
        "symbol": "EURUSD",
        "status": "closed",
        "close_reason": "GHOST_CLEANUP",
        "entry_price": 50000.0,
        "pnl": None,
    }
    assert not _is_displayable_closed_trade(ghost)


def test_closed_trade_requires_real_exit_and_pnl():
    incomplete = {
        "symbol": "EURUSD",
        "status": "closed",
        "entry_price": 1.1,
        "pnl": None,
    }
    valid = {
        "symbol": "EURUSD",
        "status": "closed",
        "entry_price": 1.1,
        "exit_price": 1.105,
        "pnl": 50.0,
    }
    assert not _is_displayable_closed_trade(incomplete)
    assert _is_displayable_closed_trade(valid)


def test_dashboard_uses_threaded_http_server():
    server = DashboardServer(host="127.0.0.1", port=0)
    server.start()
    try:
        assert isinstance(server.server, ThreadingHTTPServer)
    finally:
        server.stop()
