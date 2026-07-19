import json
from collections import defaultdict

trades = []
with open('superbot/logs/trades.jsonl', 'r') as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                trades.append(json.loads(line))
            except:
                pass

closed = [t for t in trades if t.get('status') == 'closed']
opened = [t for t in trades if t.get('status') != 'closed']

total_pnl = sum(t.get('pnl', 0) for t in closed)
wins = [t for t in closed if t.get('pnl', 0) > 0]
losses = [t for t in closed if t.get('pnl', 0) <= 0]
win_rate = len(wins)/len(closed)*100 if closed else 0

print("=== STATS GLOBALES ===")
print(f"Total trades fermes: {len(closed)}")
print(f"PnL total: {total_pnl:.2f} USDT")
print(f"Wins: {len(wins)} | Losses: {len(losses)}")
print(f"Win rate: {win_rate:.1f}%")
avg_win = sum(t.get('pnl',0) for t in wins)/len(wins) if wins else 0
avg_loss = sum(t.get('pnl',0) for t in losses)/len(losses) if losses else 0
print(f"Gain moyen: {avg_win:.2f} | Perte moyenne: {avg_loss:.2f}")
if avg_loss != 0:
    print(f"Ratio R/R effectif: {abs(avg_win/avg_loss):.2f}")

# Par symbol
by_sym = defaultdict(lambda: {'pnl':0,'wins':0,'losses':0,'trades':0})
for t in closed:
    s = t.get('symbol','?')
    by_sym[s]['pnl'] += t.get('pnl',0)
    by_sym[s]['trades'] += 1
    if t.get('pnl',0) > 0:
        by_sym[s]['wins'] += 1
    else:
        by_sym[s]['losses'] += 1

print("\n=== PAR SYMBOL ===")
for s, d in sorted(by_sym.items(), key=lambda x: -x[1]['pnl']):
    wr = d['wins']/d['trades']*100 if d['trades'] else 0
    print(f"{s:15s} PnL={d['pnl']:+8.2f} | {d['trades']} trades | WR={wr:.0f}%")

# Par broker
by_broker = defaultdict(lambda: {'pnl':0,'trades':0,'wins':0})
for t in closed:
    b = t.get('broker','?')
    by_broker[b]['pnl'] += t.get('pnl',0)
    by_broker[b]['trades'] += 1
    if t.get('pnl',0) > 0:
        by_broker[b]['wins'] += 1

print("\n=== PAR BROKER ===")
for b, d in sorted(by_broker.items(), key=lambda x: -x[1]['pnl']):
    wr = d['wins']/d['trades']*100 if d['trades'] else 0
    print(f"{b:12s} PnL={d['pnl']:+8.2f} | {d['trades']} trades | WR={wr:.0f}%")

# Score analysis (from open signals)
scored = [t for t in trades if 'signal_score' in t]
print(f"\n=== SIGNAUX ANALYSES (open+closed avec score): {len(scored)} ===")
if scored:
    scores = [t.get('signal_score',0) for t in scored]
    print(f"Score moyen: {sum(scores)/len(scores):.1f} | Min: {min(scores)} | Max: {max(scores)}")
    regimes = defaultdict(int)
    for t in scored:
        regimes[t.get('market_regime','?')] += 1
    for r, cnt in sorted(regimes.items(), key=lambda x: -x[1]):
        print(f"  Regime {r}: {cnt} signaux")

# PnL par mois/semaine
print("\n=== EVOLUTION TEMPORELLE ===")
by_date = defaultdict(float)
for t in closed:
    ts = t.get('timestamp','')[:10]
    if ts:
        by_date[ts] += t.get('pnl',0)
for d in sorted(by_date.keys()):
    bar = '+' * int(max(0, by_date[d]/5)) if by_date[d] > 0 else '-' * int(max(0, -by_date[d]/5))
    print(f"  {d}: {by_date[d]:+7.2f} USDT  {bar}")

# 10 derniers trades
print("\n=== 10 DERNIERS TRADES FERMES ===")
for t in closed[-10:]:
    pnl = t.get('pnl',0)
    sym = t.get('symbol','?')
    ts = t.get('timestamp','?')[:16]
    tgt = t.get('target', '?')
    broker = t.get('broker','?')
    print(f"{ts} [{broker:7s}] {sym:15s} PnL={pnl:+7.2f}  target={tgt}")

# Worst trades
print("\n=== PIRES TRADES ===")
for t in sorted(closed, key=lambda x: x.get('pnl',0))[:5]:
    pnl = t.get('pnl',0)
    sym = t.get('symbol','?')
    ts = t.get('timestamp','?')[:16]
    print(f"{ts} {sym:15s} PnL={pnl:+7.2f}")

# Best trades
print("\n=== MEILLEURS TRADES ===")
for t in sorted(closed, key=lambda x: -x.get('pnl',0))[:5]:
    pnl = t.get('pnl',0)
    sym = t.get('symbol','?')
    ts = t.get('timestamp','?')[:16]
    print(f"{ts} {sym:15s} PnL={pnl:+7.2f}")

# Positions en cours
print(f"\n=== POSITIONS OUVERTES: {len(opened)} ===")
for t in opened[-10:]:
    sym = t.get('symbol','?')
    ts = t.get('timestamp','?')[:16]
    score = t.get('signal_score','?')
    broker = t.get('broker','?')
    entry = t.get('entry_price',0)
    sl = t.get('stop_loss',0)
    tp = t.get('take_profit',0)
    print(f"{ts} [{broker:7s}] {sym:15s} entry={entry} SL={sl:.4f} TP={tp:.4f} score={score}")
