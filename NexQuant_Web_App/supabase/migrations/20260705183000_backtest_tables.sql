-- Migration pour la Phase 4 : Tables de Backtest

-- 1. Table des résultats globaux de backtest
CREATE TABLE IF NOT EXISTS public.backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    initial_balance NUMERIC NOT NULL,
    final_balance NUMERIC NOT NULL,
    net_profit NUMERIC NOT NULL,
    profit_factor NUMERIC NOT NULL,
    win_rate NUMERIC NOT NULL,
    total_trades INTEGER NOT NULL,
    max_drawdown NUMERIC NOT NULL,
    strategy_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Table des trades associés à un backtest
CREATE TABLE IF NOT EXISTS public.backtest_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_id UUID NOT NULL REFERENCES public.backtest_results(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_time TIMESTAMP WITH TIME ZONE NOT NULL,
    entry_price NUMERIC NOT NULL,
    exit_price NUMERIC NOT NULL,
    position_size NUMERIC NOT NULL,
    pnl NUMERIC NOT NULL,
    pnl_percent NUMERIC NOT NULL,
    duration_minutes INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Index pour optimiser les requêtes
CREATE INDEX idx_backtest_results_user_id ON public.backtest_results(user_id);
CREATE INDEX idx_backtest_trades_backtest_id ON public.backtest_trades(backtest_id);

-- Activation de RLS
ALTER TABLE public.backtest_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.backtest_trades ENABLE ROW LEVEL SECURITY;

-- Politiques RLS : L'utilisateur ne voit que ses propres backtests
CREATE POLICY "Les utilisateurs peuvent voir leurs propres résultats de backtest"
ON public.backtest_results FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Les utilisateurs peuvent créer leurs propres résultats de backtest"
ON public.backtest_results FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Les utilisateurs peuvent voir les trades de leurs backtests"
ON public.backtest_trades FOR SELECT
USING (EXISTS (
    SELECT 1 FROM public.backtest_results
    WHERE backtest_results.id = backtest_trades.backtest_id
    AND backtest_results.user_id = auth.uid()
));

CREATE POLICY "Les utilisateurs peuvent insérer des trades dans leurs backtests"
ON public.backtest_trades FOR INSERT
WITH CHECK (EXISTS (
    SELECT 1 FROM public.backtest_results
    WHERE backtest_results.id = backtest_trades.backtest_id
    AND backtest_results.user_id = auth.uid()
));
