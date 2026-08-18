import React, { useState, useEffect } from "react";
import { Shield } from "lucide-react";
import { cn } from "@/lib/utils";

const translations = {
  fr: {
    title: "Respect de votre vie privée (RGPD)",
    desc: "Nous utilisons des cookies essentiels au bon fonctionnement (gating de licence) et des outils de mesure anonymes. Vous pouvez configurer ou accepter nos conditions dans notre ",
    link: "Politique de Confidentialité",
    decline: "Refuser les cookies tiers",
    accept: "Tout accepter"
  },
  en: {
    title: "Respecting your privacy (GDPR)",
    desc: "We use cookies essential for proper operation (license gating) and anonymous measurement tools. You can configure or accept our terms in our ",
    link: "Privacy Policy",
    decline: "Decline third-party cookies",
    accept: "Accept all"
  },
  es: {
    title: "Respetando su privacidad (RGPD)",
    desc: "Utilizamos cookies esenciales para el buen funcionamiento (gating de licencia) y herramientas de medición anónimas. Puede configurar o aceptar nuestros términos en nuestra ",
    link: "Política de Privacidad",
    decline: "Rechazar cookies de terceros",
    accept: "Aceptar todo"
  }
};

export interface GDPRBannerProps {
  className?: string;
  privacyPolicyUrl?: string;
}

export const GDPRBanner: React.FC<GDPRBannerProps> = ({
  className,
  privacyPolicyUrl = "/legal/privacy",
}) => {
  const [show, setShow] = useState(false);
  const [lang, setLang] = useState<"fr" | "en" | "es">("fr");

  useEffect(() => {
    const consent = localStorage.getItem("nexquant_gdpr_consent");
    if (!consent) {
      setShow(true);
    }
    
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("lang") as "fr" | "en" | "es";
      if (stored && stored !== lang) setLang(stored);
    }
    const handleLangChange = () => {
      setLang((localStorage.getItem("lang") as "fr" | "en" | "es") || "fr");
    };
    window.addEventListener("langChange", handleLangChange);
    return () => window.removeEventListener("langChange", handleLangChange);
  }, []);

  const t = translations[lang] || translations.fr;

  const handleAcceptAll = () => {
    localStorage.setItem("nexquant_gdpr_consent", "all");
    setShow(false);
  };

  const handleDeclineAll = () => {
    localStorage.setItem("nexquant_gdpr_consent", "essential");
    setShow(false);
  };

  if (!show) return null;

  return (
    <div
      className={cn(
        "fixed bottom-6 inset-x-6 z-[999] max-w-4xl mx-auto rounded-xl border border-border bg-background/95 p-5 shadow-2xl backdrop-blur-lg animate-in slide-in-from-bottom duration-300",
        className
      )}
    >
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded bg-primary/10 border border-primary/20 text-primary shrink-0">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-foreground">
              {t.title}
            </h4>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              {t.desc}
              <a href={privacyPolicyUrl} className="text-primary hover:underline font-semibold">
                {t.link}
              </a>
              .
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 md:self-end">
          <button
            onClick={handleDeclineAll}
            className="text-xs text-muted-foreground hover:text-foreground px-3 py-2 rounded bg-transparent hover:bg-muted/30 transition-all cursor-pointer"
          >
            {t.decline}
          </button>
          <button
            onClick={handleAcceptAll}
            className="text-xs font-semibold text-primary-foreground bg-primary hover:bg-primary/90 px-4 py-2.5 rounded-lg shadow-lg transition-all cursor-pointer"
          >
            {t.accept}
          </button>
        </div>
      </div>
    </div>
  );
};

export default GDPRBanner;
