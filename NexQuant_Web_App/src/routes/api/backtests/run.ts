import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { exec } from "child_process";
import { promisify } from "util";
import fs from "fs/promises";
import path from "path";

const execAsync = promisify(exec);

const BacktestParamsSchema = z.object({
  user_id: z.string().uuid(),
  symbol: z.string().min(1),
  timeframe: z.string().default("1h"),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  initial_balance: z.number().default(10000),
});

export const Route = createFileRoute("/api/backtests/run")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const rawBody = await request.text();
        let body: unknown;
        try {
          body = JSON.parse(rawBody);
        } catch {
          return json({ error: "Invalid JSON" }, 400);
        }

        const parsed = BacktestParamsSchema.safeParse(body);
        if (!parsed.success) {
          return json({ error: "Invalid payload", details: parsed.error.flatten() }, 400);
        }

        // Authentification simple pour sécuriser la route interne
        const claimedUser = request.headers.get("x-user-id");
        if (!claimedUser || claimedUser !== parsed.data.user_id) {
          return json({ error: "Unauthorized" }, 401);
        }

        const { user_id, symbol, timeframe, initial_balance } = parsed.data;

        // Préparer les chemins
        const projectRoot = path.resolve(process.cwd(), "..", "nexquant");
        const pythonScript = path.join(projectRoot, "optimize_rules.py");
        const reportFile = path.join(projectRoot, "backtest_report.json");

        try {
          // Lancer le script python en mode backtest pur avec output JSON
          // Note: On suppose que optimize_rules.py est modifié pour accepter ces arguments
          // et générer un rapport JSON exploitable.
          const cmd = `python "${pythonScript}" --run-backtest --symbol "${symbol}" --timeframe "${timeframe}" --balance ${initial_balance} --json-output "${reportFile}"`;
          
          console.log(`Exécution du backtest : ${cmd}`);
          const { stdout, stderr } = await execAsync(cmd, { cwd: projectRoot });

          // Lire le résultat généré par le script Python
          const reportRaw = await fs.readFile(reportFile, "utf-8");
          const reportJson = JSON.parse(reportRaw);

          // Insérer dans Supabase
          const { supabaseAdmin } = await import("@/integrations/supabase/client.server");

          // Insérer le résultat global
          const { data: btResult, error: btError } = await supabaseAdmin
            .from("backtest_results")
            .insert({
              user_id,
              symbol,
              timeframe,
              start_date: reportJson.start_date || new Date().toISOString(),
              end_date: reportJson.end_date || new Date().toISOString(),
              initial_balance,
              final_balance: reportJson.final_balance || initial_balance,
              net_profit: reportJson.net_profit || 0,
              profit_factor: reportJson.profit_factor || 0,
              win_rate: reportJson.win_rate || 0,
              total_trades: reportJson.total_trades || 0,
              max_drawdown: reportJson.max_drawdown || 0,
              strategy_config: reportJson.config || {},
            })
            .select()
            .single();

          if (btError) {
            console.error("Erreur d'insertion du résultat de backtest:", btError);
            return json({ error: "Failed to save backtest result" }, 500);
          }

          // Insérer les trades si existants
          if (reportJson.trades && reportJson.trades.length > 0) {
            const tradesToInsert = reportJson.trades.map((t: any) => ({
              backtest_id: btResult.id,
              symbol,
              side: t.side.toLowerCase(),
              entry_time: t.entry_time,
              exit_time: t.exit_time,
              entry_price: t.entry_price,
              exit_price: t.exit_price,
              position_size: t.size || 0,
              pnl: t.pnl || 0,
              pnl_percent: t.pnl_percent || 0,
              duration_minutes: t.duration_minutes || 0,
            }));

            const { error: tradesError } = await supabaseAdmin
              .from("backtest_trades")
              .insert(tradesToInsert);

            if (tradesError) {
              console.error("Erreur d'insertion des trades de backtest:", tradesError);
            }
          }

          return json({
            ok: true,
            message: "Backtest completed and saved successfully",
            backtest_id: btResult.id,
            results: btResult,
          });
        } catch (e) {
          console.error("Erreur lors de l'exécution du backtest:", e);
          return json({ error: e instanceof Error ? e.message : "Server error during backtest" }, 500);
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
