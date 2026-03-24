# Jumia Price Benchmark Tool

Outil de benchmark de prix entre Jumia.com.ng et ses concurrents (Konga, Slot.ng, PayPorte, Fouanistore).

---

## Déploiement en ligne (Render.com) — Guide pas à pas

### Étape 1 — Créer un compte GitHub
Aller sur https://github.com et créer un compte.

### Étape 2 — Créer un dépôt
1. Cliquer "+" → "New repository"
2. Nommer : `jumia-benchmark`, laisser en Public
3. Cliquer "Create repository"

### Étape 3 — Uploader les fichiers
Sur la page du dépôt, cliquer "uploading an existing file" et glisser tous les fichiers du projet. Cliquer "Commit changes".

### Étape 4 — Créer un compte Render
Aller sur https://render.com et s'inscrire avec GitHub.

### Étape 5 — Déployer
1. Dashboard Render → "New +" → "Web Service"
2. Choisir le dépôt `jumia-benchmark`
3. Render détecte render.yaml automatiquement
4. Cliquer "Create Web Service"
5. Attendre 2-3 minutes

Vous obtenez une URL `https://jumia-benchmark.onrender.com` à partager à votre équipe.

---

## Utilisation

- Saisie manuelle : SKUs séparés par virgules ou retours à la ligne
- Import fichier : CSV ou Excel avec colonne "SKU"
- Export : bouton "⬇ Export Excel" après analyse

---

## Notes

- Plan gratuit Render : mise en veille après 15 min d'inactivité (plan Starter $7/mois pour éviter ça)
- Limite : 50 SKUs par analyse (modifiable dans app.py)
- Si un concurrent affiche "—" : son site bloque les requêtes automatiques
