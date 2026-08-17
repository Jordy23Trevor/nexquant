"""Calibration walk-forward du score par symbole/classe d'actif (sans overfit).

Principe : on ne choisit les signaux prédictifs QUE sur la fenêtre d'entraînement
(passé), puis on évalue le score résultant sur la fenêtre de test (futur),
sans jamais regarder le futur pour choisir les signaux. Compare :
  - le plein échantillon (in-sample, ce qu'on serait tenté de calibrer) ;
  - le hors-échantillon (out-of-sample, ce qui compte vraiment).

Lit artifacts/trade_signals_wf.csv (généré par collect_trades_wf.py).

Usage :
    python artifacts/walk_forward_calibrate.py
"""

import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "artifacts" / "trade_signals_wf.csv"

SIGNALS = [
    "sig_adx", "sig_dist_ema_atr", "sig_rsi", "sig_bb_percent",
    "sig_macd_hist_slope", "sig_vol_ratio", "sig_atr_rank", "sig_donchian_pos",
]


def pf(sub: pd.DataFrame) -> float:
    if len(sub) == 0:
        return float("nan")
    wins = sub[sub["pnl"] > 0]["pnl"].sum()
    losses = abs(sub[sub["pnl"] < 0]["pnl"].sum())
    return wins / losses if losses > 0 else float("inf")


def wr(sub: pd.DataFrame) -> float:
    return sub["winner"].mean() if len(sub) else float("nan")


def signal_edges(train: pd.DataFrame) -> dict:
    """Edge (ΔPF) de chaque signal sur la fenêtre d'entraînement + direction."""
    out = {}
    for sig in SIGNALS:
        s = train[train[sig].notna()]
        if len(s) < 12:
            continue
        med = s[sig].median()
        hi = s[s[sig] > med]
        lo = s[s[sig] <= med]
        if len(hi) < 5 or len(lo) < 5:
            continue
        if pf(hi) >= pf(lo):
            out[sig] = {"dir": "high", "edge": pf(hi) - pf(lo)}
        else:
            out[sig] = {"dir": "low", "edge": pf(lo) - pf(hi)}
    return out


def select_signals(train: pd.DataFrame, top_n: int = 3, min_edge: float = 0.0):
    edges = signal_edges(train)
    ranked = sorted(edges.items(), key=lambda kv: -kv[1]["edge"])
    selected = [(sig, meta) for sig, meta in ranked if meta["edge"] > min_edge][:top_n]
    return selected, edges


def score_trades(sub: pd.DataFrame, selected, train: pd.DataFrame) -> pd.Series:
    """+1 par signal du bon côté (seuil = médiane TRAIN)."""
    scores = pd.Series(0.0, index=sub.index)
    for sig, meta in selected:
        med = train[train[sig].notna()][sig].median()
        if meta["dir"] == "high":
            scores += (sub[sig] > med).astype(float)
        else:
            scores += (sub[sig] <= med).astype(float)
    return scores


def eval_split(train: pd.DataFrame, test: pd.DataFrame, top_n: int = 3):
    selected, _ = select_signals(train, top_n=top_n)
    if not selected:
        return None
    scores = score_trades(test, selected, train)
    test = test.assign(score=scores)
    base_wr = wr(test)
    base_pf = pf(test)
    # Séparation haut/bas par le score calibré (sans seuil arbitraire)
    med = test["score"].median()
    top = test[test["score"] > med]
    bot = test[test["score"] <= med]
    degenerate = len(top) == 0 or len(bot) == 0
    rho = stats.spearmanr(test["score"], test["winner"]).statistic if len(test) >= 4 and not degenerate else float("nan")
    top_pf_delta = (pf(top) - base_pf) if not degenerate else float("nan")
    return {
        "n_test": len(test), "n_sel": len(selected),
        "signals": ",".join(s for s, _ in selected),
        "base_wr": base_wr, "base_pf": base_pf,
        "top_wr": wr(top), "top_pf": pf(top),
        "bot_wr": wr(bot), "bot_pf": pf(bot),
        "top_pf_delta": top_pf_delta, "rho": rho,
        "degenerate": degenerate,
        "test_scores": list(test["score"]), "test_winners": list(test["winner"]),
    }


def fmt(r: dict) -> str:
    if r is None:
        return "  (pas de signal sélectionnable)"
    if r.get("degenerate"):
        return (f"  test n={r['n_test']:<3} signaux={r['n_sel']} [{r['signals']}]\n"
                f"    base WR/PF = {r['base_wr']*100:4.1f}% / {r['base_pf']:.2f} | "
                f"score DÉGÉNÉRÉ (variance nulle sur le test)")
    return (f"  test n={r['n_test']:<3} signaux={r['n_sel']} [{r['signals']}]\n"
            f"    base WR/PF = {r['base_wr']*100:4.1f}% / {r['base_pf']:.2f} | "
            f"haut = {r['top_wr']*100:4.1f}% / {r['top_pf']:.2f} | "
            f"bas = {r['bot_wr']*100:4.1f}% / {r['bot_pf']:.2f} | "
            f"ΔPF haut={r['top_pf_delta']:+.2f} ρ={r['rho']:+.2f}")


def main() -> int:
    df = pd.read_csv(CSV)
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)
    df = df.sort_values("entry_time")

    print("=" * 82)
    print("  WALK-FORWARD : calibration sur train (passé) → évaluation sur test (futur)")
    print("=" * 82)

    rows = []
    for symbol, sub in df.groupby("symbol"):
        sub = sub.reset_index(drop=True)
        n = len(sub)
        if n < 20:
            print(f"\n### {symbol} : {n} trades — trop peu pour un split, ignoré")
            continue
        cut = int(n * 0.7)
        train, test = sub.iloc[:cut], sub.iloc[cut:]

        print(f"\n### {symbol} ({n} trades, split {len(train)} train / {len(test)} test)")

        # 1. Ce qu'on serait tenté de faire (in-sample, plein échantillon)
        edges = signal_edges(sub)
        ranked = sorted(edges.items(), key=lambda kv: -kv[1]["edge"])
        print("  [IN-SAMPLE] edges ΔPF (plein échantillon) :")
        for sig, meta in ranked:
            print(f"      {sig:<20} {meta['dir']:>4}  {meta['edge']:+.2f}")

        # 2. Hors-échantillon (ce qui compte)
        r = eval_split(train, test)
        print("  [OUT-OF-SAMPLE] score calibré sur train, évalué sur test :")
        print(fmt(r))
        rows.append({"symbol": symbol, **r} if r else {"symbol": symbol})

    # Synthèse hors-échantillon
    print("\n" + "=" * 82)
    print("  SYNTHÈSE HORS-ÉCHANTILLON")
    print("=" * 82)
    pooled_top_pf_delta = []
    pooled_rho = []
    for r in rows:
        if not r or "base_pf" not in r:
            continue
        delta = "deg" if r.get("degenerate") else f"{r['top_pf_delta']:+.2f}"
        rho = "deg" if r.get("degenerate") else f"{r['rho']:+.2f}"
        print(f"  {r['symbol']:<10} ΔPF(haut-base)={delta:>6}  ρ={rho:>6}")
        if not r.get("degenerate"):
            pooled_top_pf_delta.append(r["top_pf_delta"])
            pooled_rho.append(r["rho"])

    # Poolé : un seul ρ de Spearman sur TOUS les trades de test (plus robuste)
    all_scores = []
    all_winners = []
    for r in rows:
        if r and "test_scores" in r:
            all_scores.extend(r["test_scores"])
            all_winners.extend(r["test_winners"])
    if len(all_scores) >= 4:
        pooled_rho = stats.spearmanr(all_scores, all_winners).statistic
        print(f"\n  ρ(score, gain) POOLÉ sur tous les tests = {pooled_rho:+.3f}")

    if pooled_rho is not None:
        import numpy as np
        print(f"  Moyenne ΔPF(haut vs base) = {np.mean(pooled_top_pf_delta):+.2f} "
              f"(>0 = le score sépare les gagnants)" if pooled_top_pf_delta else "  (ΔPF indisponible : scores dégénérés)")
        print(f"  Moyenne ρ(score, gain)   = {np.mean(pooled_rho):+.2f} "
              f"(>0 = corrélation positive)" if isinstance(pooled_rho, list) else "")
        print("\n  Interprétation : un score utile doit montrer ΔPF > 0 ET ρ > 0 "
              "HORS échantillon. S'il est positif in-sample mais ~0/négatif "
              "out-of-sample, l'edge apparent était de l'overfit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
