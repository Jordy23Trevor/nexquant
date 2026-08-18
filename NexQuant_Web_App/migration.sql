-- Migration to add advanced telemetry metrics to bot_status

ALTER TABLE public.bot_status 
ADD COLUMN IF NOT EXISTS kelly_fraction numeric(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS news_sentiment numeric(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS fear_greed numeric(5,2) DEFAULT 50,
ADD COLUMN IF NOT EXISTS uptime_seconds integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS regime VARCHAR(255),
ADD COLUMN IF NOT EXISTS regime_confidence FLOAT DEFAULT 0,
ADD COLUMN IF NOT EXISTS daily_achieved_eur FLOAT DEFAULT 0,
ADD COLUMN IF NOT EXISTS daily_target_eur FLOAT DEFAULT 0,
ADD COLUMN IF NOT EXISTS win_rate FLOAT DEFAULT 0,
ADD COLUMN IF NOT EXISTS profit_factor FLOAT DEFAULT 1;
