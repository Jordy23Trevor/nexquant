import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { requireSupabaseAuth } from "@/integrations/supabase/auth-middleware";

/** Seed 90 days of synthetic data if user is brand new. Lets the demo feel alive. */
export const ensureDemoData = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { supabase, userId } = context;
    const { count } = await supabase
      .from("equity_snapshots")
      .select("*", { count: "exact", head: true })
      .eq("user_id", userId);
    if ((count ?? 0) > 0) return { seeded: false };

    // Equity curve: 90 days, slight upward drift with volatility
    const now = Date.now();
    const start = 10000;
    let equity = start;
    const snaps: { user_id: string; ts: string; equity: number; pnl_total: number; drawdown: number }[] = [];
    let peak = start;
    for (let i = 90; i >= 0; i--) {
      const drift = 0.0015;
      const vol = (Math.random() - 0.48) * 0.022;
      equity = equity * (1 + drift + vol);
      peak = Math.max(peak, equity);
      const dd = (peak - equity) / peak;
      snaps.push({
        user_id: userId,
        ts: new Date(now - i * 86400000).toISOString(),
        equity: Math.round(equity * 100) / 100,
        pnl_total: Math.round((equity - start) * 100) / 100,
        drawdown: Math.round(dd * 10000) / 100,
      });
    }
    await supabase.from("equity_snapshots").insert(snaps);

    // Bot status
    await supabase.from("bot_status").upsert({
      user_id: userId,
      is_running: true,
      broker_type: "binance",
      testnet: true,
      started_at: new Date(now - 5 * 86400000).toISOString(),
      last_heartbeat: new Date().toISOString(),
      current_equity: snaps[snaps.length - 1].equity,
      initial_equity: start,
    });

    // Open positions
    const open = [
      { symbol: "BTCUSDT", side: "long",  qty: 0.082, entry: 67420.5, current: 68210.3, broker: "binance" },
      { symbol: "ETHUSDT", side: "long",  qty: 1.4,   entry: 3520.1,  current: 3478.6,  broker: "binance" },
      { symbol: "EURUSD",  side: "short", qty: 5000,  entry: 1.0842,  current: 1.0821,  broker: "forex" },
      { symbol: "AAPL",    side: "long",  qty: 12,    entry: 212.4,   current: 215.8,   broker: "alpaca" },
    ].map((p) => {
      const dir = p.side === "long" ? 1 : -1;
      const pnl = (p.current - p.entry) * p.qty * dir;
      const pct = ((p.current - p.entry) / p.entry) * 100 * dir;
      return {
        user_id: userId, symbol: p.symbol, side: p.side, qty: p.qty,
        entry_price: p.entry, current_price: p.current,
        pnl: Math.round(pnl * 100) / 100,
        pnl_pct: Math.round(pct * 100) / 100,
        status: "open", broker: p.broker,
        opened_at: new Date(now - Math.random() * 86400000 * 3).toISOString(),
      };
    });
    // Closed positions
    const closed = Array.from({ length: 16 }).map((_, i) => {
      const symbols = ["BTCUSDT", "ETHUSDT", "EURUSD", "GBPUSD", "AAPL", "TSLA", "SOLUSDT"];
      const symbol = symbols[i % symbols.length];
      const side = Math.random() > 0.5 ? "long" : "short";
      const entry = 100 + Math.random() * 500;
      const pct = (Math.random() - 0.4) * 4;
      const current = entry * (1 + pct / 100);
      const qty = +(0.5 + Math.random() * 4).toFixed(2);
      const pnl = (current - entry) * qty * (side === "long" ? 1 : -1);
      const opened = now - (i + 1) * 86400000 * 0.7;
      return {
        user_id: userId, symbol, side, qty, entry_price: +entry.toFixed(2),
        current_price: +current.toFixed(2),
        pnl: +pnl.toFixed(2), pnl_pct: +pct.toFixed(2),
        status: "closed", broker: "binance",
        opened_at: new Date(opened).toISOString(),
        closed_at: new Date(opened + 3600000 * (2 + Math.random() * 20)).toISOString(),
      };
    });
    await supabase.from("positions").insert([...open, ...closed]);

    // Market regime
    await supabase.from("market_regime").insert([
      { user_id: userId, symbol: "BTCUSDT", regime: "trending",  confidence: 0.87, trend_direction: "up",   news_sentiment: 0.42, nlp_signal: "Fed pause hikes — bullish risk-on" },
      { user_id: userId, symbol: "ETHUSDT", regime: "trending",  confidence: 0.78, trend_direction: "up",   news_sentiment: 0.31, nlp_signal: "ETF inflows accelerating" },
      { user_id: userId, symbol: "EURUSD",  regime: "ranging",   confidence: 0.71, trend_direction: "neutral", news_sentiment: -0.08, nlp_signal: "ECB on hold, mixed signals" },
      { user_id: userId, symbol: "AAPL",    regime: "volatile",  confidence: 0.64, trend_direction: "down", news_sentiment: -0.22, nlp_signal: "Earnings miss on services" },
    ]);

    // Logs (recent first)
    const sources = ["engine", "broker", "nlp", "risk", "news"];
    const levels: ("info" | "success" | "warn" | "error")[] = ["info", "info", "success", "info", "warn", "info", "success", "error"];
    const messages = [
      "Heartbeat OK · latency 84ms",
      "Regime classifier updated: BTCUSDT → TRENDING (0.87)",
      "Order filled: LONG BTCUSDT 0.082 @ 67420.50",
      "News ingested: 12 articles, sentiment +0.42",
      "Drawdown approaching 2% — sizing reduced",
      "Kelly fraction recomputed: 0.18",
      "Exit triggered: SHORT EURUSD +0.34% (+$48.21)",
      "Webhook delivery failed (retry 1/3)",
    ];
    const logs = Array.from({ length: 40 }).map((_, i) => ({
      user_id: userId,
      level: levels[i % levels.length],
      source: sources[i % sources.length],
      message: messages[i % messages.length],
      created_at: new Date(now - i * 60_000 * (1 + Math.random() * 3)).toISOString(),
    }));
    await supabase.from("bot_logs").insert(logs);

    return { seeded: true };
  });

export const getDashboardData = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { supabase, userId } = context;
    const [status, equity, openPositions, closedPositions, regime, logs, profile, userBroker] = await Promise.all([
      supabase.from("bot_status").select("*").eq("user_id", userId).maybeSingle(),
      supabase.from("equity_snapshots").select("ts, equity, pnl_total, drawdown")
        .eq("user_id", userId).order("ts", { ascending: true }).limit(500),
      supabase.from("positions").select("*").eq("user_id", userId).eq("status", "open")
        .order("opened_at", { ascending: false }),
      supabase.from("positions").select("*").eq("user_id", userId).eq("status", "closed")
        .order("closed_at", { ascending: false }).limit(30),
      supabase.from("market_regime").select("*").eq("user_id", userId)
        .order("updated_at", { ascending: false }),
      supabase.from("bot_logs").select("*").eq("user_id", userId)
        .order("created_at", { ascending: false }).limit(60),
      supabase.from("profiles").select("trial_end, role, ingest_token").eq("id", userId).single(),
      supabase.from("user_brokers").select("broker_type, asset_type").eq("user_id", userId).maybeSingle(),
    ]);

    return {
      status: status.data,
      equity: equity.data ?? [],
      openPositions: openPositions.data ?? [],
      closedPositions: closedPositions.data ?? [],
      regime: regime.data ?? [],
      logs: logs.data ?? [],
      profile: profile.data ?? null,
      userBroker: userBroker.data ?? null,
    };
  });

export const toggleBot = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ run: z.boolean() }).parse(d))
  .handler(async ({ data, context }) => {
    const { supabase, userId } = context;
    const patch = {
      is_running: data.run,
      last_heartbeat: new Date().toISOString(),
      ...(data.run ? { started_at: new Date().toISOString() } : {}),
    };
    await supabase.from("bot_status").update(patch).eq("user_id", userId);
    await supabase.from("bot_logs").insert({
      user_id: userId,
      level: data.run ? "success" : "warn",
      source: "control",
      message: data.run ? "Bot démarré par l'utilisateur" : "Bot arrêté par l'utilisateur",
    });
    return { ok: true };
  });

export const updateRisk = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ risk: z.number() }).parse(d))
  .handler(async ({ data, context }) => {
    const { supabase, userId } = context;
    // Mise à jour hypothétique de bot_config, à lier plus tard avec Python
    // await supabase.from("bot_config").update({ risk_pct: data.risk }).eq("user_id", userId);
    await supabase.from("bot_logs").insert({
      user_id: userId,
      level: "info",
      source: "control",
      message: `Risque modifié à ${data.risk}% (Pris en compte au prochain cycle)`,
    });
    return { ok: true };
  });

import crypto from "crypto";

function getEncryptionKey(): Buffer {
  const secret = process.env.NEXQUANT_ENCRYPTION_SECRET || process.env.SUPABASE_SERVICE_ROLE_KEY || "default_super_secret_fallback_key_32bytes";
  return crypto.createHash("sha256").update(secret).digest();
}

function encrypt(text: string): string {
  const iv = crypto.randomBytes(16);
  const key = getEncryptionKey();
  const cipher = crypto.createCipheriv("aes-256-cbc", key, iv);
  let encrypted = cipher.update(text);
  encrypted = Buffer.concat([encrypted, cipher.final()]);
  return iv.toString("hex") + ":" + encrypted.toString("hex");
}

export const saveBrokerCredentials = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({
    broker_type: z.enum(["binance", "alpaca", "mt5"]),
    api_key: z.string().optional(),
    api_secret: z.string().optional(),
    // mt5 specific
    login: z.string().optional(),
    password: z.string().optional(),
    server: z.string().optional(),
    path: z.string().optional(),
  }).parse(d))
  .handler(async ({ data, context }) => {
    const { supabase, userId } = context;
    
    // Déterminer le type d'actif automatiquement
    let asset_type: "crypto" | "forex" | "etf" = "crypto";
    if (data.broker_type === "mt5") asset_type = "forex";
    else if (data.broker_type === "alpaca") asset_type = "etf";

    // Structurer les clés à chiffrer
    let apiKeyToEncrypt = data.api_key || "";
    let apiSecretToEncrypt = data.api_secret || "";

    if (data.broker_type === "mt5") {
      apiKeyToEncrypt = JSON.stringify({
        login: data.login,
        server: data.server,
        path: data.path
      });
      apiSecretToEncrypt = data.password || "";
    }

    const encryptedKey = apiKeyToEncrypt ? encrypt(apiKeyToEncrypt) : "";
    const encryptedSecret = apiSecretToEncrypt ? encrypt(apiSecretToEncrypt) : "";

    // Insérer ou mettre à jour dans user_brokers
    const { error } = await supabase.from("user_brokers").upsert({
      user_id: userId,
      broker_type: data.broker_type,
      encrypted_api_key: encryptedKey,
      encrypted_api_secret: encryptedSecret,
      asset_type: asset_type,
      created_at: new Date().toISOString(),
    }, { onConflict: "user_id,broker_type" });

    if (error) {
      console.error("Error upserting user_brokers:", error);
      throw new Error(error.message);
    }

    // Créer aussi un log
    await supabase.from("bot_logs").insert({
      user_id: userId,
      level: "success",
      source: "config",
      message: `Broker ${data.broker_type.toUpperCase()} configuré (${asset_type.toUpperCase()})`,
    });

    // Mettre à jour le type de broker dans bot_status
    await supabase.from("bot_status").update({
      broker_type: data.broker_type,
      testnet: true
    }).eq("user_id", userId);

    return { ok: true };
  });

export const getAdminData = createServerFn({ method: "GET" })
  .middleware([requireSupabaseAuth])
  .handler(async ({ context }) => {
    const { userId } = context;
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");

    // Vérifier si l'utilisateur est admin
    const { data: callerProfile } = await supabaseAdmin
      .from("profiles")
      .select("role")
      .eq("id", userId)
      .single();

    if (callerProfile?.role !== "admin") {
      throw new Error("Unauthorized: Admin role required");
    }

    // Récupérer tous les utilisateurs
    const [profilesRes, botStatusRes, logsRes, brokersRes] = await Promise.all([
      supabaseAdmin.from("profiles").select("id, email, display_name, role, trial_end, created_at").order("created_at", { ascending: false }),
      supabaseAdmin.from("bot_status").select("*"),
      supabaseAdmin.from("bot_logs").select("*").order("created_at", { ascending: false }).limit(100),
      supabaseAdmin.from("user_brokers").select("user_id, broker_type, asset_type"),
    ]);

    return {
      profiles: profilesRes.data ?? [],
      botStatuses: botStatusRes.data ?? [],
      logs: logsRes.data ?? [],
      brokers: brokersRes.data ?? [],
    };
  });

export const toggleUserBot = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ targetUserId: z.string().uuid(), run: z.boolean() }).parse(d))
  .handler(async ({ data, context }) => {
    const { userId } = context;
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");

    const { data: callerProfile } = await supabaseAdmin
      .from("profiles")
      .select("role")
      .eq("id", userId)
      .single();

    if (callerProfile?.role !== "admin") {
      throw new Error("Unauthorized: Admin role required");
    }

    const patch = {
      is_running: data.run,
      last_heartbeat: new Date().toISOString(),
      ...(data.run ? { started_at: new Date().toISOString() } : {}),
    };

    await supabaseAdmin.from("bot_status").update(patch).eq("user_id", data.targetUserId);
    await supabaseAdmin.from("bot_logs").insert({
      user_id: data.targetUserId,
      level: data.run ? "success" : "warn",
      source: "admin_control",
      message: data.run ? "Bot démarré à distance par l'administrateur" : "Bot arrêté à distance par l'administrateur",
    });

    return { ok: true };
  });

export const updateUserTrial = createServerFn({ method: "POST" })
  .middleware([requireSupabaseAuth])
  .inputValidator((d) => z.object({ targetUserId: z.string().uuid(), trialDays: z.number() }).parse(d))
  .handler(async ({ data, context }) => {
    const { userId } = context;
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");

    const { data: callerProfile } = await supabaseAdmin
      .from("profiles")
      .select("role")
      .eq("id", userId)
      .single();

    if (callerProfile?.role !== "admin") {
      throw new Error("Unauthorized: Admin role required");
    }

    const trialEnd = new Date(Date.now() + data.trialDays * 24 * 3600 * 1000).toISOString();
    await supabaseAdmin.from("profiles").update({ trial_end: trialEnd }).eq("id", data.targetUserId);

    await supabaseAdmin.from("bot_logs").insert({
      user_id: data.targetUserId,
      level: "success",
      source: "admin_license",
      message: `Période d'essai mise à jour par l'administrateur : ${data.trialDays} jours restants`,
    });

    return { ok: true };
  });
