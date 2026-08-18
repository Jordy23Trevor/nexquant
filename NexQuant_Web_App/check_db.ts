import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve('./.env') });

const supabase = createClient(process.env.VITE_SUPABASE_URL!, process.env.VITE_SUPABASE_ANON_KEY!);

async function main() {
  const { data: users, error: err } = await supabase.from('profiles').select('id, email');
  if (err) {
    console.error(err);
    return;
  }
  for (const user of users) {
    const { data: status } = await supabase.from('bot_status').select('*').eq('user_id', user.id).maybeSingle();
    console.log(`User ${user.email}: bot_status = ${status ? JSON.stringify(status) : 'MISSING'}`);
  }
}
main();
