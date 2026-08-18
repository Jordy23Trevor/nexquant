import fs from 'fs';

const envContent = fs.readFileSync('.env', 'utf8');
const SUPABASE_URL = envContent.match(/VITE_SUPABASE_URL=(.+)/)?.[1]?.trim();
const SUPABASE_KEY = envContent.match(/VITE_SUPABASE_ANON_KEY=(.+)/)?.[1]?.trim();

async function main() {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/bot_status?select=*`, {
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`
    }
  });
  const data = await res.json();
  console.log('Bot statuses:', JSON.stringify(data, null, 2));
}

main();
