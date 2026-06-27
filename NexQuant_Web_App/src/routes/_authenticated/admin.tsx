import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { useState } from "react";
import {
  Activity, ArrowLeft, Bot, Shield, Clock, Power, Play, Pause, RefreshCw, Key, LogOut
} from "lucide-react";
import { toast } from "sonner";
import { getAdminData, toggleUserBot, updateUserTrial } from "@/lib/nexquant.functions";
import { supabase } from "@/integrations/supabase/client";

export const Route = createFileRoute("/_authenticated/admin")({
  head: () => ({ meta: [{ title: "Admin Portal — NexQuant" }] }),
  component: AdminDashboard,
});

function AdminDashboard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fetchData = useServerFn(getAdminData);
  const toggleBotFn = useServerFn(toggleUserBot);
  const updateTrialFn = useServerFn(updateUserTrial);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["adminData"],
    queryFn: () => fetchData(),
    refetchInterval: 10000,
  });

  const [extendingUserId, setExtendingUserId] = useState<string | null>(null);
  const [extendDays, setExtendDays] = useState(30);

  const toggleMutation = useMutation({
    mutationFn: (vars: { targetUserId: string; run: boolean }) =>
      toggleBotFn({ data: vars }),
    onSuccess: () => {
      toast.success("Statut du bot utilisateur mis à jour !");
      qc.invalidateQueries({ queryKey: ["adminData"] });
    },
    onError: (err: any) => {
      toast.error(`Erreur: ${err.message}`);
    }
  });

  const trialMutation = useMutation({
    mutationFn: (vars: { targetUserId: string; trialDays: z.infer<any> }) =>
      updateTrialFn({ data: vars }),
    onSuccess: () => {
      toast.success("Licence utilisateur mise à jour !");
      setExtendingUserId(null);
      qc.invalidateQueries({ queryKey: ["adminData"] });
    },
    onError: (err: any) => {
      toast.error(`Erreur: ${err.message}`);
    }
  });

  async function signOut() {
    await qc.cancelQueries();
    qc.clear();
    await supabase.auth.signOut();
    navigate({ to: "/auth", replace: true });
  }

  if (isLoading || !data) {
    return (
      <div className="min-h-screen grid place-items-center bg-background text-foreground">
        <div className="flex items-center gap-3 text-muted-foreground">
          <Activity className="w-5 h-5 animate-pulse text-accent" />
          Chargement du portail administrateur...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top bar */}
      <header className="sticky top-0 z-40 backdrop-blur bg-background/70 border-b border-border">
        <div className="max-w-7xl mx-auto px-4 lg:px-6 h-14 flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-accent to-destructive grid place-items-center">
              <Shield className="w-3.5 h-3.5 text-background" />
            </div>
            <span className="font-semibold tracking-tight">NexQuant Admin</span>
          </Link>
          <span className="hidden md:inline text-xs text-muted-foreground font-mono">/ surveillance globale</span>

          <div className="ml-auto flex items-center gap-2">
            <Link to="/dashboard" className="text-xs px-3 py-1.5 rounded-md bg-card hover:bg-muted/50 border border-border flex items-center gap-1.5 transition">
              <ArrowLeft className="w-3.5 h-3.5" />
              Retour Dashboard
            </Link>
            <button onClick={() => refetch()} disabled={isFetching}
              className="p-1.5 rounded-md hover:bg-card text-muted-foreground" title="Rafraîchir">
              <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
            </button>
            <button onClick={signOut} className="p-1.5 rounded-md hover:bg-card text-muted-foreground" title="Déconnexion">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 lg:px-6 py-6 space-y-6">
        {/* KPI Row */}
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="panel p-4 bg-card border border-border rounded-lg">
            <div className="text-xs uppercase text-muted-foreground">Utilisateurs inscrits</div>
            <div className="mt-2 text-2xl font-semibold font-mono text-foreground">{data.profiles.length}</div>
          </div>
          <div className="panel p-4 bg-card border border-border rounded-lg">
            <div className="text-xs uppercase text-muted-foreground">Bots en cours de trading</div>
            <div className="mt-2 text-2xl font-semibold font-mono text-success">
              {data.botStatuses.filter(b => b.is_running).length}
            </div>
          </div>
          <div className="panel p-4 bg-card border border-border rounded-lg">
            <div className="text-xs uppercase text-muted-foreground">Version Client Stable</div>
            <div className="mt-2 text-2xl font-semibold font-mono text-accent">v2.0.0</div>
          </div>
          <div className="panel p-4 bg-card border border-border rounded-lg">
            <div className="text-xs uppercase text-muted-foreground">Essais actifs</div>
            <div className="mt-2 text-2xl font-semibold font-mono text-warning">
              {data.profiles.filter(p => p.trial_end && new Date(p.trial_end) > new Date()).length}
            </div>
          </div>
        </section>

        {/* User Bots List */}
        <section className="panel p-5 bg-card border border-border rounded-lg">
          <h2 className="font-semibold mb-4 text-lg">Bots Clients Déployés</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm font-mono">
              <thead>
                <tr className="text-xs uppercase text-muted-foreground border-b border-border">
                  <th className="text-left py-2 pr-3">Utilisateur</th>
                  <th className="text-left py-2 pr-3">Courtier</th>
                  <th className="text-center py-2 pr-3">Statut Bot</th>
                  <th className="text-left py-2 pr-3">Fin de Licence / Essai</th>
                  <th className="text-right py-2 pr-3">Dernière Activité</th>
                  <th className="text-right py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.profiles.map((user) => {
                  const bot = data.botStatuses.find((b) => b.user_id === user.id);
                  const broker = data.brokers.find((br) => br.user_id === user.id);
                  const isExpired = user.trial_end ? new Date() > new Date(user.trial_end) : false;
                  
                  return (
                    <tr key={user.id} className="border-b border-border/50 hover:bg-muted/10">
                      <td className="py-3 pr-3">
                        <div className="font-medium text-foreground">{user.display_name || "Sans Nom"}</div>
                        <div className="text-xs text-muted-foreground font-mono">{user.email}</div>
                      </td>
                      <td className="py-3 pr-3 capitalize">
                        {broker ? `${broker.broker_type} (${broker.asset_type})` : "Non configuré"}
                      </td>
                      <td className="py-3 pr-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${
                          bot?.is_running 
                            ? "bg-success/15 text-success" 
                            : "bg-muted text-muted-foreground"
                        }`}>
                          {bot?.is_running ? "ACTIF" : "PAUSE"}
                        </span>
                      </td>
                      <td className="py-3 pr-3">
                        {user.trial_end ? (
                          <div className="flex flex-col">
                            <span className={isExpired ? "text-destructive font-semibold" : "text-foreground"}>
                              {new Date(user.trial_end).toLocaleDateString()}
                            </span>
                            <span className="text-[10px] text-muted-foreground">
                              {isExpired ? "Expiré" : `${Math.ceil((new Date(user.trial_end).getTime() - Date.now()) / (24*3600*1000))}j restants`}
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">Illimité / Admin</span>
                        )}
                      </td>
                      <td className="py-3 pr-3 text-right text-xs text-muted-foreground">
                        {bot?.last_heartbeat ? new Date(bot.last_heartbeat).toLocaleString() : "Aucun signal"}
                      </td>
                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => toggleMutation.mutate({ targetUserId: user.id, run: !bot?.is_running })}
                            disabled={toggleMutation.isPending}
                            className={`p-1.5 rounded-md hover:bg-muted transition text-xs flex items-center gap-1 ${
                              bot?.is_running ? "text-warning" : "text-success"
                            }`}
                            title={bot?.is_running ? "Suspendre le bot" : "Reprendre le trading"}
                          >
                            {bot?.is_running ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                          </button>
                          
                          <button
                            onClick={() => setExtendingUserId(extendingUserId === user.id ? null : user.id)}
                            className="p-1.5 rounded hover:bg-muted text-primary text-xs"
                            title="Modifier licence"
                          >
                            <Clock className="w-4 h-4" />
                          </button>
                        </div>

                        {extendingUserId === user.id && (
                          <div className="mt-2 p-3 bg-muted/30 border border-border rounded text-left space-y-2">
                            <label className="block text-xs text-muted-foreground font-semibold">Prolonger la licence (jours)</label>
                            <div className="flex gap-2">
                              <input
                                type="number"
                                value={extendDays}
                                onChange={(e) => setExtendDays(Number(e.target.value))}
                                className="w-20 bg-card border border-border rounded px-2 py-1 text-xs"
                              />
                              <button
                                onClick={() => trialMutation.mutate({ targetUserId: user.id, trialDays: extendDays })}
                                className="px-2 py-1 rounded bg-primary text-background font-semibold text-xs"
                              >
                                Appliquer
                              </button>
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* Global Logs Stream */}
        <section className="panel p-5 bg-card border border-border rounded-lg">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-4 h-4 text-destructive" />
            <h2 className="font-semibold text-lg">Journal de Surveillance des Logs Systèmes</h2>
          </div>
          <div className="bg-background/50 border border-border rounded-md p-4 h-96 overflow-y-auto font-mono text-xs space-y-2">
            {data.logs.map((log) => {
              const profile = data.profiles.find((p) => p.id === log.user_id);
              const color =
                log.level === "error" ? "text-destructive" :
                log.level === "warn" ? "text-warning" :
                log.level === "success" ? "text-success" :
                "text-muted-foreground";

              return (
                <div key={log.id} className="flex gap-2 leading-relaxed hover:bg-muted/10 p-0.5 rounded">
                  <span className="text-muted-foreground/60 shrink-0">
                    {new Date(log.created_at).toLocaleTimeString()}
                  </span>
                  <span className="text-accent shrink-0 font-semibold truncate max-w-[120px]" title={profile?.email}>
                    [{profile?.display_name || profile?.email || log.user_id.slice(0,8)}]
                  </span>
                  <span className={`${color} shrink-0`}>[{log.source || log.level}]</span>
                  <span className="text-foreground/90">{log.message}</span>
                </div>
              );
            })}
            {data.logs.length === 0 && <div className="text-muted-foreground text-center py-10">Aucun log enregistré</div>}
          </div>
        </section>
      </main>
    </div>
  );
}
