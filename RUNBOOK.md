# Runbook Incident - Dashboard sans donnees

1. Verifier la sante API+DB: ouvrir `<VITE_API_BASE>/health` (ou `/api/health`); si `status=ok` et HTTP `200`, passer a l'etape 2, sinon incident backend/DB (HTTP `503`).
2. Ouvrir la console navigateur (F12) et relever les logs `[API_RETRY]` / `[API_ERROR]` (url, status/code, timestamp, attempt).
3. Verifier les logs backend a la meme minute (Render service `planification-api`) pour confirmer: timeout, erreur SQL, redemarrage, ou surcharge.
4. Si backend indisponible: verifier l'etat Render + connexion DB, puis redemarrer le service si necessaire et re-tester `/health`.
5. Informer l'equipe avec cause + heure + action appliquee (ex: "API degradee, redemarrage effectue, retour a la normale a HH:MM UTC").

## Prevention anti-sleep

- Keep-alive actif via GitHub Actions: `.github/workflows/keep-api-awake.yml` (ping `/health` toutes les 10 minutes).
- Configurer le secret `KEEPALIVE_HEALTH_URL` dans le repo (ex: `https://project-plan.onrender.com/health`).
- Option robuste: passer le service Render sur une offre always-on pour supprimer les cold starts.
