import { createClient } from '@supabase/supabase-js';
import fs from 'fs';

const envContent = fs.readFileSync('.env', 'utf8');
const SUPABASE_URL = envContent.match(/VITE_SUPABASE_URL=(.+)/)?.[1]?.trim().replace(/"/g, '');
const SUPABASE_KEY = envContent.match(/SUPABASE_SERVICE_ROLE_KEY=(.+)/)?.[1]?.trim().replace(/"/g, '');

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

async function main() {
  console.log("Adding columns to bot_status...");
  const res = await supabase.rpc('execute_sql', { sql: `
    ALTER TABLE public.bot_status 
    ADD COLUMN IF NOT EXISTS kelly_fraction numeric(5,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS news_sentiment numeric(5,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS fear_greed numeric(5,2) DEFAULT 50,
    ADD COLUMN IF NOT EXISTS uptime_seconds integer DEFAULT 0;
  ` });
  console.log("Result:", res);
}

main();
