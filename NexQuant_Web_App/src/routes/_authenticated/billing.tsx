import { createFileRoute } from "@tanstack/react-router";
import { Check, Star, Zap } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/_authenticated/billing")({
  head: () => ({ meta: [{ title: "Facturation — NexQuant" }] }),
  component: BillingPage,
});

function BillingPage() {
  const plans = [
    {
      name: "Starter",
      price: "19",
      desc: "Idéal pour débuter le trading algorithmique.",
      features: ["1 Connexion Broker", "1 Stratégie active", "Backtests basiques", "Support communautaire"],
      popular: false,
      current: false
    },
    {
      name: "Pro",
      price: "49",
      desc: "Pour les traders exigeants voulant diversifier.",
      features: ["3 Connexions Brokers", "5 Stratégies actives", "Signaux Webhook en temps réel", "Support prioritaire 24/7"],
      popular: true,
      current: true
    },
    {
      name: "Professional",
      price: "99",
      desc: "Hébergement dédié et API privée.",
      features: ["Brokers illimités", "Stratégies illimitées", "Serveur dédié & Latence ultra-faible", "Accès API complet & Webhooks avancés"],
      popular: false,
      current: false
    }
  ];

  const handleSubscribe = () => {
    toast.info("L'intégration Lemon Squeezy est en cours de développement.");
  };

  return (
    <div className="p-4 lg:p-6 max-w-7xl mx-auto space-y-8">
      <div className="text-center max-w-2xl mx-auto mb-10">
        <h1 className="text-2xl font-bold text-zinc-100 font-technical tracking-tight mb-2">Gérez votre licence NexQuant</h1>
        <p className="text-sm text-zinc-400">Passez à la vitesse supérieure. Bénéficiez d'infrastructures dédiées et de connexions courtiers illimitées.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map((p) => (
          <div key={p.name} className={`relative panel p-6 rounded-2xl border ${p.popular ? 'border-indigo-500/50 bg-indigo-950/10 shadow-[0_0_30px_rgba(99,102,241,0.1)]' : 'border-white/10 bg-zinc-900/40'} backdrop-blur-md flex flex-col`}>
            {p.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-indigo-500 text-white text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 shadow-lg">
                <Star className="w-3 h-3 fill-white" />
                Le plus choisi
              </div>
            )}
            
            <div className="mb-6">
              <h3 className="text-lg font-bold text-zinc-100">{p.name}</h3>
              <p className="text-xs text-zinc-500 mt-1">{p.desc}</p>
            </div>
            
            <div className="mb-6 flex items-baseline gap-1">
              <span className="text-3xl font-bold font-technical text-white">${p.price}</span>
              <span className="text-xs text-zinc-500">/mois</span>
            </div>
            
            <ul className="space-y-3 mb-8 flex-1">
              {p.features.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-zinc-300">
                  <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
            
            <button 
              onClick={handleSubscribe}
              disabled={!p.current}
              className={`w-full py-2.5 rounded-xl font-medium text-xs transition ${
                p.current 
                  ? 'border border-white/10 bg-white/5 text-zinc-400 cursor-default' 
                  : 'border border-white/10 bg-zinc-900/50 text-zinc-500 cursor-not-allowed'
              }`}
            >
              {p.current ? 'Plan Actuel (Bêta)' : 'Service indisponible'}
            </button>
          </div>
        ))}
      </div>

      <div className="panel p-6 rounded-xl border border-indigo-500/20 bg-indigo-950/20 backdrop-blur-md mt-10 max-w-3xl mx-auto flex flex-col md:flex-row items-center gap-6">
        <div className="w-12 h-12 rounded-full bg-indigo-500/20 flex items-center justify-center shrink-0">
          <Zap className="w-6 h-6 text-indigo-400" />
        </div>
        <div>
          <h4 className="text-sm font-bold text-zinc-100 mb-1">Besoin d'une solution sur-mesure ?</h4>
          <p className="text-xs text-zinc-400">Contactez-nous pour un déploiement On-Premise ou des stratégies quantitatives personnalisées.</p>
        </div>
        <button className="md:ml-auto px-4 py-2 rounded-lg bg-white/10 text-zinc-200 text-xs font-medium hover:bg-white/20 border border-white/10 whitespace-nowrap transition">
          Contacter l'équipe
        </button>
      </div>
    </div>
  );
}
