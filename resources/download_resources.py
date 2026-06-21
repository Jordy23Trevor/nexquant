"""
Script de téléchargement des ressources recommandées pour NexQuant.
Télécharge les livres (via Anna's Archive), scrape les blogs,
et récupère les articles académiques.
"""

import os
import sys
import json
import time
import hashlib
import logging
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

# --- Configuration ---
BASE_DIR = Path(__file__).parent
BOOKS_DIR = BASE_DIR / "books"
BLOGS_DIR = BASE_DIR / "blogs"
PAPERS_DIR = BASE_DIR / "papers"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CREDS_FILE = BASE_DIR / "credentials.json"
STATUS_FILE = BASE_DIR / "download_status.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("resource_downloader")

# --- Dépendances ---
def ensure_deps():
    """Installe les dépendances manquantes."""
    deps = ["requests", "beautifulsoup4", "markdownify", "lxml"]
    for dep in deps:
        try:
            __import__(dep.replace("-", "").replace("4", ""))
        except ImportError:
            log.info(f"Installation de {dep}...")
            os.system(f"{sys.executable} -m pip install {dep} -q")

ensure_deps()

import requests
from bs4 import BeautifulSoup
try:
    from markdownify import markdownify as md
except ImportError:
    md = lambda html, **kw: BeautifulSoup(html, "lxml").get_text()

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
})

# ============================================================
# RESSOURCES À TÉLÉCHARGER
# ============================================================

BOOKS = [
    {"title": "Trading Psychology 2.0", "author": "Brett N. Steenbarger",
     "search": "Trading Psychology 2.0 Steenbarger", "category": "psychology"},
    {"title": "The Little Book of Behavioral Investing", "author": "James Montier",
     "search": "Little Book Behavioral Investing Montier", "category": "psychology"},
    {"title": "Technical Analysis of the Financial Markets", "author": "John J. Murphy",
     "search": "Technical Analysis Financial Markets Murphy", "category": "technical_analysis"},
    {"title": "Algorithmic Trading", "author": "Ernest Chan",
     "search": "Algorithmic Trading Winning Strategies Ernest Chan", "category": "quant"},
    {"title": "Cryptoassets", "author": "Chris Burniske & Jack Tatar",
     "search": "Cryptoassets Innovative Investor Guide Burniske Tatar", "category": "crypto"},
    {"title": "Forex Price Action Scalping", "author": "Bob Volman",
     "search": "Forex Price Action Scalping Volman", "category": "forex"},
    {"title": "The Hacking of the American Mind", "author": "Robert Lustig",
     "search": "Hacking American Mind Lustig", "category": "psychology"},
]

BLOGS = [
    {"name": "QuantStart", "url": "https://www.quantstart.com/articles/",
     "category": "technical_analysis",
     "description": "Tutoriels Python pour indicateurs avancés (Ichimoku, Vortex, FAMA)"},
    {"name": "QuantInsti", "url": "https://quantinsti.com/blog/",
     "category": "quant",
     "description": "Stratégies intraday, volatilité, sentiment news"},
    {"name": "CoinShares Research", "url": "https://coinshares.com/research",
     "category": "crypto",
     "description": "Flux institutionnels, corrélations BTC/actions/or"},
    {"name": "NBER Working Papers", "url": "https://www.nber.org/papers?page=1&perPage=50&q=finance+trading",
     "category": "quant",
     "description": "Études macro pertinentes pour le trading"},
    {"name": "Newfound Research", "url": "https://newfoundresearch.com/blog/",
     "category": "quant",
     "description": "Facteurs, allocation, risque"},
]

# Blogs avec problèmes connus
BLOGS_WITH_ISSUES = [
    {"name": "Trading Composure", "url": "https://tradingcomposure.com/",
     "status": "TIMEOUT", "category": "psychology",
     "alternative": "Contenu similaire disponible sur: https://www.investopedia.com/trading-psychology-4689669",
     "description": "Discipline, routines pré/post-marché, journaling"},
    {"name": "Santiment Blog", "url": "https://santiment.net/blog/",
     "status": "404", "category": "crypto",
     "alternative": "Utiliser Glassnode Academy: https://academy.glassnode.com/",
     "description": "Métriques on-chain avancées"},
    {"name": "Glassnode Insights", "url": "https://glassnode.com/insights",
     "status": "404", "category": "crypto",
     "alternative": "Utiliser Glassnode Academy: https://academy.glassnode.com/",
     "description": "Comportement whales, activité développeur, NVT"},
    {"name": "Forex Factory", "url": "https://www.forexfactory.com/",
     "status": "403_BLOCKED", "category": "forex",
     "alternative": "Utiliser BabyPips: https://www.babypips.com/forexpedia ou TradingView: https://www.tradingview.com/",
     "description": "Stratégies réelles partagées par traders pro"},
    {"name": "Journal of Portfolio Management", "url": "https://journals.pm-research.com/",
     "status": "DNS_FAIL", "category": "quant",
     "alternative": "Accès via SSRN: https://www.ssrn.com/ ou Google Scholar",
     "description": "Facteurs (value, momentum), allocation dynamique"},
]

PAPERS = [
    {"title": "Profitability of Technical Analysis", "authors": "Park & Irwin (2007)",
     "url": "https://www.tandfonline.com/doi/abs/10.1080/00036846.2007.11052301",
     "category": "technical_analysis", "status": "403_PAYWALL",
     "alternatives": [
         "https://www.researchgate.net/publication/228261644",
         "https://ageconsearch.umn.edu/record/37818",
     ],
     "description": "Méta-analyse de 95 études sur la rentabilité de l'AT"},
]

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def load_status():
    if STATUS_FILE.exists():
        return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    return {"books": {}, "blogs": {}, "papers": {}, "updated_at": None}

def save_status(status):
    status["updated_at"] = datetime.now().isoformat()
    STATUS_FILE.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")

def safe_filename(name):
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()

def fetch_page(url, timeout=15):
    """Récupère une page web avec gestion d'erreurs."""
    try:
        resp = SESSION.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp
    except Exception as e:
        log.warning(f"Erreur fetch {url}: {e}")
        return None

# ============================================================
# 1. TÉLÉCHARGEMENT DES LIVRES
# ============================================================

ANNAS_ARCHIVE_DOMAINS = [
    "annas-archive.se",
    "annas-archive.li",
    "annas-archive.gs",
]

def search_annas_archive(query):
    """Cherche un livre sur Anna's Archive."""
    for domain in ANNAS_ARCHIVE_DOMAINS:
        url = f"https://{domain}/search?q={requests.utils.quote(query)}&ext=pdf"
        log.info(f"  Recherche sur {domain}...")
        resp = fetch_page(url, timeout=20)
        if resp and resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            # Cherche les liens vers les pages de détail
            results = []
            for a in soup.select("a[href*='/md5/']"):
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if title and href:
                    results.append({"title": title[:120], "url": f"https://{domain}{href}"})
            if results:
                return domain, results[:5]
        time.sleep(1)
    return None, []

def download_from_annas(detail_url, dest_path, domain):
    """Tente le téléchargement depuis la page de détail Anna's Archive."""
    resp = fetch_page(detail_url)
    if not resp:
        return False
    soup = BeautifulSoup(resp.text, "lxml")
    # Chercher les liens de téléchargement
    dl_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        if any(k in text for k in ["download", "télécharger", "libgen", "slow"]):
            if href.startswith("http"):
                dl_links.append(href)
            elif href.startswith("/"):
                dl_links.append(f"https://{domain}{href}")

    for link in dl_links[:3]:
        log.info(f"    Tentative DL: {link[:80]}...")
        try:
            r = SESSION.get(link, timeout=60, stream=True, allow_redirects=True)
            if r.status_code == 200 and len(r.content) > 10000:
                content_type = r.headers.get("content-type", "")
                if "pdf" in content_type or "octet" in content_type or dest_path.suffix == ".pdf":
                    dest_path.write_bytes(r.content)
                    log.info(f"    ✅ Téléchargé: {dest_path.name} ({len(r.content)//1024} KB)")
                    return True
        except Exception as e:
            log.warning(f"    Échec DL: {e}")
        time.sleep(2)
    return False

def try_archive_org(title, author, dest_path):
    """Tente Internet Archive (archive.org) comme alternative."""
    query = f"{title} {author}"
    url = f"https://archive.org/search?query={requests.utils.quote(query)}&mediatype=texts"
    resp = fetch_page(url)
    if not resp:
        return False
    soup = BeautifulSoup(resp.text, "lxml")
    for item in soup.select(".item-ia")[:3]:
        link = item.find("a", href=True)
        if link:
            item_url = f"https://archive.org{link['href']}"
            log.info(f"    Archive.org trouvé: {item_url}")
            # Note: archive.org nécessite souvent un emprunt, pas de DL direct
    return False

def download_books(status):
    """Télécharge tous les livres."""
    log.info("=" * 60)
    log.info("📚 TÉLÉCHARGEMENT DES LIVRES")
    log.info("=" * 60)
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)

    for book in BOOKS:
        title = book["title"]
        fname = safe_filename(f"{book['author']} - {title}.pdf")
        dest = BOOKS_DIR / fname

        if dest.exists() and dest.stat().st_size > 10000:
            log.info(f"✅ Déjà présent: {fname}")
            status["books"][title] = {"status": "ALREADY_EXISTS", "path": str(dest)}
            continue

        log.info(f"\n📖 Recherche: {title} — {book['author']}")

        # 1. Essayer Anna's Archive
        domain, results = search_annas_archive(book["search"])
        downloaded = False
        if results:
            log.info(f"  {len(results)} résultat(s) trouvé(s) sur {domain}")
            for r in results[:3]:
                log.info(f"    → {r['title'][:80]}")
                if download_from_annas(r["url"], dest, domain):
                    downloaded = True
                    status["books"][title] = {
                        "status": "DOWNLOADED",
                        "path": str(dest),
                        "source": f"annas-archive ({domain})",
                    }
                    break
                time.sleep(2)

        # 2. Essayer Archive.org
        if not downloaded:
            log.info(f"  Tentative Archive.org...")
            if try_archive_org(title, book["author"], dest):
                downloaded = True

        # 3. Marquer comme non trouvé avec instructions
        if not downloaded:
            status["books"][title] = {
                "status": "NOT_FOUND",
                "instructions": (
                    f"Livre non trouvé automatiquement. Pour le télécharger manuellement:\n"
                    f"1. Allez sur Anna's Archive (vérifiez le domaine actuel sur Wikipedia)\n"
                    f"2. Cherchez: '{book['search']}'\n"
                    f"3. Ou essayez: https://archive.org/search?query={requests.utils.quote(book['search'])}\n"
                    f"4. Ou achetez-le sur Amazon/Kobo/Fnac\n"
                    f"5. Placez le PDF dans: {BOOKS_DIR}"
                ),
            }
            log.warning(f"  ⚠️ Non trouvé: {title}")

        time.sleep(3)

# ============================================================
# 2. SCRAPING DES BLOGS
# ============================================================

def scrape_blog_articles(blog, max_articles=15):
    """Scrape les articles d'un blog et les sauvegarde en markdown."""
    name = blog["name"]
    blog_dir = BLOGS_DIR / safe_filename(name)
    blog_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"\n🌐 Scraping: {name} ({blog['url']})")
    resp = fetch_page(blog["url"])
    if not resp:
        return {"status": "FAILED", "error": "Impossible d'accéder au site"}

    soup = BeautifulSoup(resp.text, "lxml")
    # Extraire les liens d'articles
    articles = []
    base_url = f"{urlparse(blog['url']).scheme}://{urlparse(blog['url']).netloc}"

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if len(text) > 15 and len(text) < 200:
            full_url = href if href.startswith("http") else urljoin(base_url, href)
            # Filtrer les URLs de navigation
            if any(skip in full_url.lower() for skip in [
                "login", "signup", "register", "cart", "privacy",
                "terms", "contact", "about", "#", "javascript"
            ]):
                continue
            if full_url not in [a["url"] for a in articles]:
                articles.append({"title": text, "url": full_url})

    articles = articles[:max_articles]
    log.info(f"  {len(articles)} articles trouvés")

    saved = 0
    for i, article in enumerate(articles):
        try:
            art_resp = fetch_page(article["url"], timeout=10)
            if not art_resp:
                continue
            art_soup = BeautifulSoup(art_resp.text, "lxml")

            # Extraire le contenu principal
            content_el = (
                art_soup.find("article") or
                art_soup.find("main") or
                art_soup.find("div", class_=re.compile(r"(content|post|article|entry)", re.I)) or
                art_soup.find("body")
            )
            if not content_el:
                continue

            # Supprimer nav, footer, sidebar
            for tag in content_el.find_all(["nav", "footer", "aside", "script", "style"]):
                tag.decompose()

            content_md = md(str(content_el), heading_style="ATX", strip=["img", "form"])
            if len(content_md) < 200:
                continue

            # Header markdown
            article_md = f"# {article['title']}\n\n"
            article_md += f"> Source: {article['url']}\n"
            article_md += f"> Blog: {name}\n"
            article_md += f"> Catégorie: {blog['category']}\n"
            article_md += f"> Téléchargé: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            article_md += "---\n\n"
            article_md += content_md

            fname = safe_filename(article["title"][:80]) + ".md"
            (blog_dir / fname).write_text(article_md, encoding="utf-8")
            saved += 1
            time.sleep(1)
        except Exception as e:
            log.warning(f"  Erreur article '{article['title'][:50]}': {e}")

    log.info(f"  ✅ {saved}/{len(articles)} articles sauvegardés dans {blog_dir}")
    return {"status": "OK", "articles_found": len(articles), "articles_saved": saved, "path": str(blog_dir)}

def scrape_blogs(status):
    """Scrape tous les blogs accessibles."""
    log.info("\n" + "=" * 60)
    log.info("🌐 SCRAPING DES BLOGS & SITES")
    log.info("=" * 60)

    for blog in BLOGS:
        result = scrape_blog_articles(blog)
        status["blogs"][blog["name"]] = result
        time.sleep(2)

    # Blogs avec problèmes: sauvegarder les alternatives
    for blog in BLOGS_WITH_ISSUES:
        log.warning(f"\n⚠️ {blog['name']}: {blog['status']}")
        log.info(f"  Alternative: {blog['alternative']}")
        status["blogs"][blog["name"]] = {
            "status": blog["status"],
            "original_url": blog["url"],
            "alternative": blog["alternative"],
            "description": blog["description"],
        }
        # Essayer de scraper l'alternative
        alt_url = blog["alternative"].split(": ")[-1] if ": " in blog["alternative"] else None
        if alt_url and alt_url.startswith("http"):
            alt_blog = {
                "name": f"{blog['name']} (alternative)",
                "url": alt_url,
                "category": blog["category"],
                "description": blog["description"],
            }
            alt_result = scrape_blog_articles(alt_blog, max_articles=10)
            status["blogs"][f"{blog['name']}_alt"] = alt_result
            time.sleep(2)

# ============================================================
# 3. ARTICLES ACADÉMIQUES
# ============================================================

def download_papers(status):
    """Télécharge les articles académiques."""
    log.info("\n" + "=" * 60)
    log.info("📄 ARTICLES ACADÉMIQUES")
    log.info("=" * 60)
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    for paper in PAPERS:
        title = paper["title"]
        log.info(f"\n📄 {title} — {paper['authors']}")
        log.info(f"  URL originale: {paper['url']} → {paper['status']}")

        downloaded = False
        for alt_url in paper.get("alternatives", []):
            log.info(f"  Tentative alternative: {alt_url}")
            resp = fetch_page(alt_url)
            if resp and resp.status_code == 200:
                # Sauvegarder la page en markdown
                soup = BeautifulSoup(resp.text, "lxml")
                content = soup.find("article") or soup.find("main") or soup.find("body")
                if content:
                    for tag in content.find_all(["script", "style", "nav"]):
                        tag.decompose()
                    content_md = md(str(content), heading_style="ATX")
                    fname = safe_filename(f"{paper['authors']} - {title}") + ".md"
                    dest = PAPERS_DIR / fname
                    header = f"# {title}\n\n> Auteurs: {paper['authors']}\n> Source: {alt_url}\n> Catégorie: {paper['category']}\n\n---\n\n"
                    dest.write_text(header + content_md, encoding="utf-8")
                    log.info(f"  ✅ Sauvegardé: {fname}")
                    downloaded = True
                    status["papers"][title] = {"status": "DOWNLOADED", "path": str(dest), "source": alt_url}
                    break
            time.sleep(1)

        if not downloaded:
            status["papers"][title] = {
                "status": "MANUAL_REQUIRED",
                "instructions": (
                    f"Article payant/inaccessible automatiquement.\n"
                    f"1. Cherchez sur Google Scholar: '{title} {paper['authors']}'\n"
                    f"2. Ou sur Sci-Hub / ResearchGate\n"
                    f"3. Ou demandez l'accès aux auteurs sur ResearchGate\n"
                    f"4. Placez le PDF dans: {PAPERS_DIR}"
                ),
            }

# ============================================================
# 4. INTÉGRATION AU BOT (knowledge JSON)
# ============================================================

def generate_blog_knowledge():
    """Génère des fichiers knowledge JSON à partir des blogs scrapés."""
    log.info("\n" + "=" * 60)
    log.info("🧠 GÉNÉRATION DES CONNAISSANCES")
    log.info("=" * 60)

    if not BLOGS_DIR.exists():
        return

    rules = []
    for blog_dir in BLOGS_DIR.iterdir():
        if not blog_dir.is_dir():
            continue
        blog_name = blog_dir.name
        articles = list(blog_dir.glob("*.md"))
        if not articles:
            continue

        log.info(f"  Traitement de {blog_name}: {len(articles)} articles")

        blog_rules = []
        for art_file in articles:
            content = art_file.read_text(encoding="utf-8", errors="ignore")
            # Extraire les concepts clés (heuristique simple)
            lines = content.split("\n")
            key_lines = [
                l.strip() for l in lines
                if len(l.strip()) > 30 and any(kw in l.lower() for kw in [
                    "strategy", "stratégie", "indicator", "indicateur",
                    "risk", "risque", "signal", "momentum", "volatil",
                    "mean reversion", "backtest", "sharpe", "drawdown",
                    "position size", "stop loss", "take profit",
                    "bitcoin", "crypto", "forex", "etf",
                ])
            ]
            for line in key_lines[:3]:
                rule_id = hashlib.md5(line.encode()).hexdigest()[:12]
                blog_rules.append({
                    "id": f"blog_{blog_name}_{rule_id}",
                    "category": "strategy",
                    "rule": line[:200],
                    "source": blog_name,
                    "origin": "scraped_blog",
                })

        if blog_rules:
            knowledge_file = KNOWLEDGE_DIR / f"{safe_filename(blog_name)}.json"
            knowledge_data = {
                "source": blog_name,
                "type": "blog",
                "scraped_at": datetime.now().isoformat(),
                "articles_count": len(articles),
                "rules": blog_rules[:25],
            }
            knowledge_file.write_text(
                json.dumps(knowledge_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            rules.extend(blog_rules[:25])
            log.info(f"  ✅ {len(blog_rules)} règles extraites de {blog_name}")

    log.info(f"\n  Total: {len(rules)} nouvelles règles générées")
    return rules

# ============================================================
# MAIN
# ============================================================

def main():
    log.info("🚀 NexQuant Resource Downloader")
    log.info(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info(f"   Dossier: {BASE_DIR}\n")

    # Créer les dossiers
    for d in [BOOKS_DIR, BLOGS_DIR, PAPERS_DIR, KNOWLEDGE_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    status = load_status()

    # Étape 1: Livres
    download_books(status)
    save_status(status)

    # Étape 2: Blogs
    scrape_blogs(status)
    save_status(status)

    # Étape 3: Papers
    download_papers(status)
    save_status(status)

    # Étape 4: Générer les connaissances
    generate_blog_knowledge()
    save_status(status)

    # Résumé final
    log.info("\n" + "=" * 60)
    log.info("📊 RÉSUMÉ")
    log.info("=" * 60)

    books_ok = sum(1 for b in status["books"].values() if b.get("status") in ("DOWNLOADED", "ALREADY_EXISTS"))
    blogs_ok = sum(1 for b in status["blogs"].values() if b.get("status") == "OK")
    papers_ok = sum(1 for p in status["papers"].values() if p.get("status") == "DOWNLOADED")

    log.info(f"  📚 Livres:   {books_ok}/{len(BOOKS)}")
    log.info(f"  🌐 Blogs:    {blogs_ok}/{len(BLOGS)}")
    log.info(f"  📄 Papers:   {papers_ok}/{len(PAPERS)}")
    log.info(f"\n  📁 Statut complet: {STATUS_FILE}")
    log.info(f"  🔑 Credentials: {CREDS_FILE}")

    # Afficher les actions manuelles requises
    manual = []
    for name, info in {**status["books"], **status["papers"]}.items():
        if info.get("status") in ("NOT_FOUND", "MANUAL_REQUIRED"):
            manual.append((name, info.get("instructions", "")))

    if manual:
        log.info(f"\n⚠️ {len(manual)} ACTIONS MANUELLES REQUISES:")
        for name, instr in manual:
            log.info(f"\n  📌 {name}:")
            for line in instr.split("\n"):
                log.info(f"     {line}")

if __name__ == "__main__":
    main()
