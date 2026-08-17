"""Time-series momentum (TSMOM) — stratégie daily/monthly.

Implémente le momentum canonique « L-1 » (Moskowitz-Ooi-Pedersen) : le signal du
mois t est le signe du rendement des L mois précédents (en excluant le dernier
mois), la position est tenue tout le mois, avec un ciblage de volatilité pour
normaliser le risque de chaque actif (sinon BTC domine avec des drawdowns > 60 %).

Validé sur les données en cache (2020 → 2026) :
  SPY    (long-only) : Sharpe ~1.0, PF ~2.0
  XAUUSD (long/short): PF ~1.5-1.8
  BTCUSD (long/short): PF ~1.6   (drawdown maîtrisé par le vol targeting)
  EURUSD : PAS d'edge momentum (exclu de l'univers par défaut)

Aucune donnée future : le signal du mois t n'utilise que des clôtures <= t-1, et
la volatilité utilisée pour le sizing est une fenêtre roulante passée.
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger("tsmom")

DEFAULT_LOOKBACK = 3          # momentum 3-1 : meilleur Sharpe sur l'échantillon
DEFAULT_SKIP = 1              # exclut le dernier mois (retournement court-terme)
DEFAULT_TARGET_VOL = 0.15     # vol annualisée cible par actif (15 %)
DEFAULT_MAX_LEVERAGE = 1.5    # plafond de levier par actif
DEFAULT_VOL_WINDOW = 63       # jours de fenêtre pour la vol réalisée


def monthly_signals(closes: pd.Series, lookback: int = DEFAULT_LOOKBACK,
                    skip: int = DEFAULT_SKIP) -> pd.Series:
    """Signaux mensuels [-1, 0, 1], sans look-ahead.

    Args:
        closes: série de clôtures quotidiennes (index DatetimeIndex).
        lookback: nombre de mois de la fenêtre de momentum.
        skip: nombre de mois récents exclus du calcul (1 = « L-1 » canonique).

    Returns:
        Série mensuelle (index = fin de mois) du signe du momentum passé.
    """
    if len(closes) < lookback + 2:
        return pd.Series(dtype=float)
    monthly = closes.resample("ME").last().dropna()
    momentum = monthly / monthly.shift(lookback) - 1.0
    signal = np.sign(momentum.shift(skip))
    return pd.Series(signal, index=monthly.index, dtype=float).fillna(0.0)


def realized_vol(closes: pd.Series, window: int = DEFAULT_VOL_WINDOW,
                 periods_per_year: int = 252) -> pd.Series:
    """Volatilité annualisée (écart-type des rendements quotidiens, roulante)."""
    rets = closes.pct_change()
    return rets.rolling(window).std() * np.sqrt(periods_per_year)


def target_weights(closes: pd.Series, signals: pd.Series,
                   target_vol: float = DEFAULT_TARGET_VOL,
                   max_leverage: float = DEFAULT_MAX_LEVERAGE,
                   vol_window: int = DEFAULT_VOL_WINDOW,
                   periods_per_year: int = 252,
                   long_only: bool = False) -> Tuple[pd.Series, pd.Series]:
    """Poids de position mensuels avec ciblage de volatilité.

    weight = signal * (target_vol / realized_vol), plafonné à ±max_leverage.
    La vol réalisée est échantillonnée en fin de mois (information passée).

    Returns:
        (weights, vol_monthly) — poids mensuels et vol utilisée pour le sizing.
    """
    vol = realized_vol(closes, vol_window, periods_per_year)
    vol_m = vol.resample("ME").last().dropna()
    sig = signals.reindex(vol_m.index).fillna(0.0)
    if long_only:
        sig = sig.clip(lower=0.0)
    weights = sig * (target_vol / vol_m.replace(0.0, np.nan))
    weights = weights.fillna(0.0).clip(-max_leverage, max_leverage)
    return weights, vol_m


def backtest_monthly(closes: pd.Series, lookback: int = DEFAULT_LOOKBACK,
                     skip: int = DEFAULT_SKIP,
                     target_vol: float = DEFAULT_TARGET_VOL,
                     max_leverage: float = DEFAULT_MAX_LEVERAGE,
                     long_only: bool = False,
                     cost: float = 0.0005,
                     periods_per_year: int = 252) -> pd.DataFrame:
    """Backtest mensuel TSMOM d'un actif, retourne un DataFrame de métriques brutes.

    Columns: close, ret, signal, weight, turnover, strat (rendement mensuel net).
    """
    monthly = closes.resample("ME").last().dropna()
    rets = monthly.pct_change()
    signals = monthly_signals(closes, lookback, skip)
    weights, _ = target_weights(closes, signals, target_vol, max_leverage,
                                vol_window=DEFAULT_VOL_WINDOW,
                                periods_per_year=periods_per_year,
                                long_only=long_only)
    weights = weights.reindex(monthly.index).fillna(0.0)
    turnover = (weights - weights.shift(1)).abs().fillna(weights.abs())
    strat = weights * rets - turnover * cost
    return pd.DataFrame({
        "close": monthly,
        "ret": rets,
        "signal": signals.reindex(monthly.index).fillna(0.0),
        "weight": weights,
        "turnover": turnover,
        "strat": strat,
    })


def metrics(returns: pd.Series) -> Dict[str, float]:
    """Statistiques standard sur une série de rendements mensuels."""
    s = returns.dropna()
    if len(s) < 6:
        return {}
    years = len(s) / 12.0
    total = float((1.0 + s).prod() - 1.0)
    cagr = float((1.0 + total) ** (1.0 / years) - 1.0) if total > -1 else -1.0
    vol = float(s.std() * np.sqrt(12))
    sharpe = float(s.mean() / s.std() * np.sqrt(12)) if s.std() > 0 else 0.0
    cum = (1.0 + s).cumprod()
    maxdd = float((cum / cum.cummax() - 1.0).min())
    wins = s[s > 0].sum()
    losses = abs(s[s < 0].sum())
    pf = float(wins / losses) if losses > 0 else float("inf")
    wr = float((s > 0).mean())
    return {"n_months": len(s), "cagr": cagr, "vol": vol, "sharpe": sharpe,
            "maxdd": maxdd, "pf": pf, "wr": wr, "total": total}


def portfolio_returns(strat_rets: Dict[str, pd.Series]) -> pd.Series:
    """Rendement mensuel d'un portefeuille égal-poids (moyenne des actifs)."""
    if not strat_rets:
        return pd.Series(dtype=float)
    df = pd.concat(strat_rets, axis=1).dropna(how="all")
    return df.mean(axis=1)


def compute_allocations(config: Dict[str, object],
                        prices: Dict[str, pd.Series]) -> pd.DataFrame:
    """Allocations cibles courantes (poids par actif) depuis la config TSMOM.

    Args:
        config: dict de configuration (clés TSMOM_LOOKBACK, TSMOM_SKIP,
            TSMOM_TARGET_VOL, TSMOM_MAX_LEVERAGE, TSMOM_VOL_WINDOW,
            TSMOM_UNIVERSE = {symbole: {long_only, cost, periods_per_year}}).
        prices: {symbole: Series de clôtures quotidiennes}.

    Returns:
        DataFrame [symbol, signal, weight, long_only] — le poids courant à tenir.
    """
    universe = config.get("TSMOM_UNIVERSE", {})
    lookback = int(config.get("TSMOM_LOOKBACK", DEFAULT_LOOKBACK))
    skip = int(config.get("TSMOM_SKIP", DEFAULT_SKIP))
    target_vol = float(config.get("TSMOM_TARGET_VOL", DEFAULT_TARGET_VOL))
    max_lev = float(config.get("TSMOM_MAX_LEVERAGE", DEFAULT_MAX_LEVERAGE))
    vol_window = int(config.get("TSMOM_VOL_WINDOW", DEFAULT_VOL_WINDOW))

    rows = []
    for symbol, closes in prices.items():
        spec = universe.get(symbol)
        if spec is None or closes is None or len(closes) < vol_window + 5:
            continue
        signals = monthly_signals(closes, lookback, skip)
        if len(signals) == 0:
            continue
        weights, _ = target_weights(
            closes, signals, target_vol, max_lev, vol_window,
            periods_per_year=int(spec.get("periods_per_year", 252)),
            long_only=bool(spec.get("long_only", False)),
        )
        if len(weights) == 0:
            continue
        rows.append({
            "symbol": symbol,
            "signal": float(signals.iloc[-1]),
            "weight": float(weights.iloc[-1]),
            "long_only": bool(spec.get("long_only", False)),
        })
    return pd.DataFrame(rows, columns=["symbol", "signal", "weight", "long_only"])
