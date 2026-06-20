# NexQuant — Ressources & Mémoire du Bot

Ce dossier contient les livres et ressources de trading que le bot
intègre pour améliorer sa prise de décision.

## Structure

```
resources/
  books/            ← Déposez vos PDF, TXT ou MD ici
  knowledge/        ← Connaissances extraites par livre (JSON auto-généré)
  knowledge_index.json  ← Index global de toutes les règles (auto-généré)
  learning_engine.py    ← Script principal d'extraction
```

## Comment ajouter un livre

1. Copiez votre PDF (ou TXT/MD) dans `resources/books/`
2. Lancez le moteur d'apprentissage :
   ```bash
   python resources/learning_engine.py
   ```
3. Consultez le résumé :
   ```bash
   python resources/learning_engine.py --summary
   ```
4. **Redémarrez le bot** — il chargera automatiquement les nouvelles règles.

## Livres recommandés (déjà pré-programmés)

| Auteur             | Livre                              | Catégories couvertes             |
|--------------------|------------------------------------|----------------------------------|
| Alexander Elder    | Vivre du Trading                   | Risque, Stratégie, Signaux       |
| Thami Kabbaj       | L'Art du Trading                   | Sizing, R:R, Psychologie         |
| Mark Douglas       | Trading in the Zone                | Psychologie, Discipline          |
| Van Tharp          | Trade Your Way to Financial Freedom| SQN, R-multiples, Sizing         |
| Jesse Livermore    | Reminiscences of a Stock Operator  | Tendance, Pyramidage             |
| Jack Schwager      | Market Wizards                     | Synthèse des grands traders      |

> **Note :** Les règles de ces 6 auteurs sont déjà intégrées dans le bot
> (sans avoir besoin de leurs PDF). Ajoutez de nouveaux livres pour enrichir la base.

## Intégration dans le bot

Le bot charge l'index au démarrage :

```python
from resources.learning_engine import load_knowledge_index, get_rules_by_category

# Toutes les règles
rules = load_knowledge_index()

# Règles de gestion du risque seulement
risk_rules = get_rules_by_category("risk")
```

## Commandes utiles

```bash
# Traiter tous les nouveaux livres
python resources/learning_engine.py

# Afficher le résumé des règles chargées
python resources/learning_engine.py --summary

# Reconstruire l'index depuis zéro
python resources/learning_engine.py --reset
```
