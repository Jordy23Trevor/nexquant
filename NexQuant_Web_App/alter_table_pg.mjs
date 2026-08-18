import pg from 'pg';
import fs from 'fs';

const envContent = fs.readFileSync('.env', 'utf8');
const SUPABASE_PROJECT_ID = envContent.match(/SUPABASE_PROJECT_ID="(.+)"/)?.[1];
const DB_PASSWORD = envContent.match(/SUPABASE_DB_PASSWORD="(.+)"/)?.[1];

// encode special characters in password
const encodedPassword = encodeURIComponent(DB_PASSWORD);
const connectionString = `postgresql://postgres:${encodedPassword}@db.${SUPABASE_PROJECT_ID}.supabase.co:5432/postgres`;

const client = new pg.Client({
  connectionString,
});

async function main() {
  await client.connect();
  console.log("Connected to DB.");

  try {
    await client.query(`
      ALTER TABLE public.bot_status 
      ADD COLUMN IF NOT EXISTS kelly_fraction numeric(5,2) DEFAULT 0,
      ADD COLUMN IF NOT EXISTS news_sentiment numeric(5,2) DEFAULT 0,
      ADD COLUMN IF NOT EXISTS fear_greed numeric(5,2) DEFAULT 50,
      ADD COLUMN IF NOT EXISTS uptime_seconds integer DEFAULT 0;
    `);
    console.log("Columns added successfully!");
  } catch (err) {
    console.error("Error executing query:", err);
  } finally {
    await client.end();
  }
}

main();
