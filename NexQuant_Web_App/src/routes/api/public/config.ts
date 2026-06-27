import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import crypto from "crypto";

const ConfigSchema = z.object({
  user_id: z.string().uuid(),
  version: z.string(),
});

// Helper de déchiffrement AES-256-CBC
function getEncryptionKey(): Buffer {
  const secret = process.env.NEXQUANT_ENCRYPTION_SECRET || process.env.SUPABASE_SERVICE_ROLE_KEY || "default_super_secret_fallback_key_32bytes";
  return crypto.createHash("sha256").update(secret).digest();
}

function decrypt(encryptedText: string): string {
  try {
    const textParts = encryptedText.split(":");
    if (textParts.length < 2) return encryptedText; // Fallback si non chiffré
    const iv = Buffer.from(textParts.shift()!, "hex");
    const encrypted = Buffer.from(textParts.join(":"), "hex");
    const key = getEncryptionKey();
    const decipher = crypto.createDecipheriv("aes-256-cbc", key, iv);
    let decrypted = decipher.update(encrypted);
    decrypted = Buffer.concat([decrypted, decipher.final()]);
    return decrypted.toString("utf8");
  } catch (e) {
    console.error("Erreur de déchiffrement de clé API:", e);
    return "";
  }
}

export const Route = createFileRoute("/api/public/config")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const rawBody = await request.text();
        let body: unknown;
        try { body = JSON.parse(rawBody); }
        catch { return json({ error: "Invalid JSON" }, 400); }

        const parsed = ConfigSchema.safeParse(body);
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
        const { user_id, version } = parsed.data;

        // 1. Récupérer le profil pour valider la signature et la licence
        const { data: profile, error: profileErr } = await supabaseAdmin
          .from("profiles")
          .select("ingest_token, trial_end, role")
          .eq("id", user_id)
          .single();

        if (profileErr || !profile) {
          return json({ error: "User profile not found" }, 404);
        }

        // 2. Vérification de la signature HMAC-SHA256
        const computedSignature = crypto
          .createHmac("sha256", profile.ingest_token)
          .update(rawBody)
          .digest("hex");

        if (computedSignature !== signature) {
          return json({ error: "Unauthorized: Signature mismatch" }, 401);
        }

        // 3. Vérification de la validité de la licence (Bêta 1 mois / Stripe)
        const isTrialExpired = profile.trial_end ? new Date() > new Date(profile.trial_end) : false;
        const isAdmin = profile.role === 'admin';
        if (isTrialExpired && !isAdmin) {
          return json({ error: "License expired: trial period ended", is_expired: true }, 403);
        }

        try {
          // 4. Récupérer la configuration de trading du bot
          const { data: botConfig } = await supabaseAdmin
            .from("bot_config")
            .select("risk_pct, score_min, is_running")
            .eq("user_id", user_id)
            .maybeSingle();

          // 5. Récupérer le broker configuré et ses clés API associées
          const { data: userBroker } = await supabaseAdmin
            .from("user_brokers")
            .select("broker_type, encrypted_api_key, encrypted_api_secret, asset_type")
            .eq("user_id", user_id)
            .maybeSingle();

          // Déchiffrer les clés API à la volée avant transmission en mémoire
          let brokerData = null;
          if (userBroker) {
            const decKey = userBroker.encrypted_api_key ? decrypt(userBroker.encrypted_api_key) : "";
            const decSecret = userBroker.encrypted_api_secret ? decrypt(userBroker.encrypted_api_secret) : "";
            if (userBroker.broker_type === "mt5") {
              try {
                const parsedParams = JSON.parse(decKey);
                brokerData = {
                  broker_type: "mt5",
                  login: parsedParams.login,
                  server: parsedParams.server,
                  path: parsedParams.path,
                  password: decSecret,
                  asset_type: "forex",
                };
              } catch {
                brokerData = {
                  broker_type: "mt5",
                  api_key: decKey,
                  api_secret: decSecret,
                  asset_type: "forex",
                };
              }
            } else {
              brokerData = {
                broker_type: userBroker.broker_type,
                api_key: decKey,
                api_secret: decSecret,
                asset_type: userBroker.asset_type,
              };
            }
          }

          // 6. Vérifier la dernière version de l'application
          const { data: latestVersion } = await supabaseAdmin
            .from("app_versions")
            .select("version, download_url, changelog, is_mandatory")
            .order("created_at", { ascending: false })
            .limit(1)
            .maybeSingle();

          const updateAvailable = latestVersion ? latestVersion.version !== version : false;

          return json({
            ok: true,
            is_expired: false,
            config: botConfig || { is_running: false, risk_pct: 1.0, score_min: 6.0 },
            broker: brokerData,
            update: {
              available: updateAvailable,
              mandatory: latestVersion?.is_mandatory ?? false,
              latest_version: latestVersion?.version ?? version,
              download_url: latestVersion?.download_url ?? "",
            }
          });
        } catch (e) {
          return json({ error: e instanceof Error ? e.message : "Server error" }, 500);
        }
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
