import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import crypto from "crypto";

// Public ingest endpoint. The Python bot pushes equity / positions / logs / regime / heartbeat.
// Bypasses auth at the edge — security is enforced inside this handler using HMAC-SHA256.

const IngestSchema = z.discriminatedUnion("kind", [
  z.object({
    kind: z.literal("equity"),
    user_id: z.string().uuid(),
    payload: z.object({ equity: z.number(), pnl_total: z.number().optional(), drawdown: z.number().optional() }),
  }),
  z.object({
    kind: z.literal("heartbeat"),
    user_id: z.string().uuid(),
    payload: z.object({ is_running: z.boolean().optional(), broker_type: z.string().optional(), testnet: z.boolean().optional() }).default({}),
  }),
  z.object({
    kind: z.literal("position"),
    user_id: z.string().uuid(),
    payload: z.object({
      symbol: z.string(),
      side: z.enum(["long", "short"]),
      qty: z.number(),
      entry_price: z.number(),
      current_price: z.number(),
      pnl: z.number(),
      pnl_pct: z.number(),
      status: z.enum(["open", "closed"]).default("open"),
      broker: z.string().default("binance"),
    }),
  }),
  z.object({
    kind: z.literal("log"),
    user_id: z.string().uuid(),
    payload: z.object({
      level: z.enum(["debug", "info", "warn", "error", "success"]).default("info"),
      source: z.string().optional(),
      message: z.string(),
    }),
  }),
  z.object({
    kind: z.literal("regime"),
    user_id: z.string().uuid(),
    payload: z.object({
      symbol: z.string(),
      regime: z.enum(["trending", "ranging", "volatile"]),
      confidence: z.number(),
      trend_direction: z.enum(["up", "down", "neutral"]).optional(),
      news_sentiment: z.number().default(0),
      nlp_signal: z.string().optional(),
    }),
  }),
]);

export const Route = createFileRoute("/api/public/ingest")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const rawBody = await request.text();
        let body: unknown;
        try { body = JSON.parse(rawBody); }
        catch { return json({ error: "Invalid JSON" }, 400); }

        const parsed = IngestSchema.safeParse(body);
        if (!parsed.success) return json({ error: "Invalid payload", details: parsed.error.flatten() }, 400);

        const claimedUser = request.headers.get("x-user-id");
        if (!claimedUser || claimedUser !== parsed.data.user_id) {
          return json({ error: "Unauthorized: x-user-id missing or mismatched" }, 401);
        }

        const signature = request.headers.get("x-signature");
        if (!signature) {
          return json({ error: "Unauthorized: x-signature header missing" }, 401);
        }

        const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
        const { kind, user_id, payload } = parsed.data;

        // Récupérer le jeton d'ingestion et la fin d'essai de l'utilisateur
        const { data: profile, error: profileErr } = await supabaseAdmin
          .from("profiles")
          .select("ingest_token, trial_end, role")
          .eq("id", user_id)
          .single();

        if (profileErr || !profile) {
          return json({ error: "User profile not found" }, 404);
        }

        // 1. Vérification de la validité de la licence (Bêta 1 mois / Stripe)
        const isTrialExpired = profile.trial_end ? new Date() > new Date(profile.trial_end) : false;
        const isAdmin = profile.role === 'admin';
        if (isTrialExpired && !isAdmin) {
          return json({ error: "License expired: trial period ended" }, 403);
        }

        // 2. Vérification de la signature HMAC-SHA256
        const computedSignature = crypto
          .createHmac("sha256", profile.ingest_token)
          .update(rawBody)
          .digest("hex");

        if (computedSignature !== signature) {
          return json({ error: "Unauthorized: Signature mismatch" }, 401);
        }

        try {
          if (kind === "equity") {
            await supabaseAdmin.from("equity_snapshots").insert({
              user_id, equity: payload.equity,
              pnl_total: payload.pnl_total ?? 0,
              drawdown: payload.drawdown ?? 0,
            });
            await supabaseAdmin.from("bot_status").update({
              current_equity: payload.equity,
              last_heartbeat: new Date().toISOString(),
            }).eq("user_id", user_id);
          } else if (kind === "heartbeat") {
            await supabaseAdmin.from("bot_status").upsert({
              user_id,
              is_running: payload.is_running ?? true,
              broker_type: payload.broker_type ?? "binance",
              testnet: payload.testnet ?? true,
              last_heartbeat: new Date().toISOString(),
            });
          } else if (kind === "position") {
            if (payload.status === "open") {
              const { data: existing } = await supabaseAdmin
                .from("positions")
                .select("id")
                .eq("user_id", user_id)
                .eq("symbol", payload.symbol)
                .eq("status", "open")
                .maybeSingle();

              if (existing) {
                await supabaseAdmin
                  .from("positions")
                  .update({
                    side: payload.side,
                    qty: payload.qty,
                    entry_price: payload.entry_price,
                    current_price: payload.current_price,
                    pnl: payload.pnl,
                    pnl_pct: payload.pnl_pct,
                    broker: payload.broker,
                  })
                  .eq("id", existing.id);
              } else {
                await supabaseAdmin.from("positions").insert({
                  user_id,
                  ...payload,
                  opened_at: new Date().toISOString(),
                });
              }
            } else if (payload.status === "closed") {
              const { data: existingOpen } = await supabaseAdmin
                .from("positions")
                .select("id")
                .eq("user_id", user_id)
                .eq("symbol", payload.symbol)
                .eq("status", "open")
                .order("opened_at", { ascending: false })
                .limit(1)
                .maybeSingle();

              if (existingOpen) {
                await supabaseAdmin
                  .from("positions")
                  .update({
                    status: "closed",
                    current_price: payload.current_price,
                    pnl: payload.pnl,
                    pnl_pct: payload.pnl_pct,
                    closed_at: new Date().toISOString(),
                  })
                  .eq("id", existingOpen.id);
              } else {
                await supabaseAdmin.from("positions").insert({
                  user_id,
                  ...payload,
                  opened_at: new Date(Date.now() - 3600 * 1000).toISOString(),
                  closed_at: new Date().toISOString(),
                });
              }
            }
          } else if (kind === "log") {
            await supabaseAdmin.from("bot_logs").insert({ user_id, ...payload });
          } else if (kind === "regime") {
            await supabaseAdmin.from("market_regime").upsert(
              { user_id, ...payload, updated_at: new Date().toISOString() },
              { onConflict: "user_id,symbol" },
            );
          }
        } catch (e) {
          return json({ error: e instanceof Error ? e.message : "Server error" }, 500);
        }
        return json({ ok: true });
      },
    },
  },
});

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
