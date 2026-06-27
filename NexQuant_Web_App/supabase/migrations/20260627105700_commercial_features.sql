-- 1. Ajout des colonnes de rôle, d'essai gratuit et de jeton d'ingestion sur profiles
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin'));
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS trial_end TIMESTAMPTZ;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS ingest_token UUID NOT NULL DEFAULT gen_random_uuid();

-- Mettre à jour les profils existants pour leur attribuer 30 jours d'essai gratuit et un jeton unique par défaut
UPDATE public.profiles SET 
  trial_end = created_at + INTERVAL '30 days',
  ingest_token = COALESCE(ingest_token, gen_random_uuid())
WHERE trial_end IS NULL OR ingest_token IS NULL;

-- 2. Fonction de vérification admin (Security Definer pour éviter la récursion RLS)
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN SECURITY DEFINER AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid() AND role = 'admin'
  );
END; $$ LANGUAGE plpgsql;

-- 3. Mise à jour de la fonction d'inscription automatique pour inclure la période d'essai de 30 jours et le jeton d'ingestion
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id, email, display_name, trial_end, role, ingest_token)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email,'@',1)),
    now() + INTERVAL '30 days',
    'user',
    gen_random_uuid()
  );
  RETURN NEW;
END; $$;

-- 4. Table des courtiers et clés API (user_brokers)
CREATE TABLE IF NOT EXISTS public.user_brokers (
  id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  broker_type TEXT NOT NULL CHECK (broker_type IN ('binance', 'alpaca', 'mt5')),
  encrypted_api_key TEXT,
  encrypted_api_secret TEXT,
  asset_type TEXT NOT NULL CHECK (asset_type IN ('crypto', 'forex', 'etf')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, broker_type)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_brokers TO authenticated;
GRANT ALL ON public.user_brokers TO service_role;
ALTER TABLE public.user_brokers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "own_brokers" ON public.user_brokers 
  FOR ALL TO authenticated 
  USING (auth.uid() = user_id) 
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "admin_brokers" ON public.user_brokers 
  FOR ALL TO authenticated 
  USING (public.is_admin());

-- 5. Table des configurations de trading distantes (bot_config)
CREATE TABLE IF NOT EXISTS public.bot_config (
  user_id UUID NOT NULL PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  risk_pct NUMERIC NOT NULL DEFAULT 1.0,
  score_min NUMERIC NOT NULL DEFAULT 6.0,
  is_running BOOLEAN NOT NULL DEFAULT false,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.bot_config TO authenticated;
GRANT ALL ON public.bot_config TO service_role;
ALTER TABLE public.bot_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "own_bot_config" ON public.bot_config 
  FOR ALL TO authenticated 
  USING (auth.uid() = user_id) 
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "admin_bot_config" ON public.bot_config 
  FOR ALL TO authenticated 
  USING (public.is_admin());

-- Déclencheur pour créer automatiquement une configuration bot lors de l'inscription
CREATE OR REPLACE FUNCTION public.handle_new_user_config()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.bot_config (user_id) VALUES (NEW.id);
  RETURN NEW;
END; $$;

CREATE OR REPLACE TRIGGER on_profile_created_create_config
  AFTER INSERT ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_config();

-- Remplir la configuration pour les profils existants
INSERT INTO public.bot_config (user_id)
SELECT id FROM public.profiles ON CONFLICT DO NOTHING;

-- 6. Table des versions de l'application (app_versions)
CREATE TABLE IF NOT EXISTS public.app_versions (
  id BIGSERIAL PRIMARY KEY,
  version TEXT NOT NULL UNIQUE,
  download_url TEXT,
  changelog TEXT,
  is_mandatory BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT SELECT ON public.app_versions TO authenticated;
GRANT ALL ON public.app_versions TO service_role;
ALTER TABLE public.app_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "any_auth_read_versions" ON public.app_versions 
  FOR SELECT TO authenticated 
  USING (true);

-- 7. Ajout des politiques d'accès administrateur sur les tables existantes
CREATE POLICY "admin_select_profiles" ON public.profiles FOR SELECT TO authenticated USING (public.is_admin());
CREATE POLICY "admin_bot_status" ON public.bot_status FOR ALL TO authenticated USING (public.is_admin());
CREATE POLICY "admin_equity" ON public.equity_snapshots FOR ALL TO authenticated USING (public.is_admin());
CREATE POLICY "admin_positions" ON public.positions FOR ALL TO authenticated USING (public.is_admin());
CREATE POLICY "admin_logs" ON public.bot_logs FOR ALL TO authenticated USING (public.is_admin());
CREATE POLICY "admin_regime" ON public.market_regime FOR ALL TO authenticated USING (public.is_admin());
