import pg from 'pg';

const { Client } = pg;

const connectionString = process.env.SUPABASE_POSTGRES_URL || 'postgresql://postgres.khjeziurxksrmbrrdnlm:A$s9$q47Nf$8d@aws-0-eu-central-1.pooler.supabase.com:6543/postgres';

const client = new Client({
  connectionString,
  ssl: {
    rejectUnauthorized: false
  }
});

async function runMigration() {
  try {
    await client.connect();
    console.log('Connecté à la base de données Supabase.');

    const sql = `
      ALTER TABLE public.bot_status
      ADD COLUMN IF NOT EXISTS regime VARCHAR(255),
      ADD COLUMN IF NOT EXISTS regime_confidence FLOAT DEFAULT 0,
      ADD COLUMN IF NOT EXISTS daily_achieved_eur FLOAT DEFAULT 0,
      ADD COLUMN IF NOT EXISTS daily_target_eur FLOAT DEFAULT 0,
      ADD COLUMN IF NOT EXISTS win_rate FLOAT DEFAULT 0,
      ADD COLUMN IF NOT EXISTS profit_factor FLOAT DEFAULT 1;
    `;

    await client.query(sql);
    console.log('Colonnes de télémétrie V3 ajoutées avec succès à bot_status !');

  } catch (err) {
    console.error('Erreur lors de la migration :', err);
  } finally {
    await client.end();
    console.log('Déconnecté.');
  }
}

runMigration();
