# 🚀 GUIDE DE DÉPLOIEMENT RAPIDE - IvoirCyberScan V1

## ⏱️ Déploiement en 5 minutes chrono !

### Minute 1 : Créer un compte GitHub
1. Va sur https://github.com
2. Clique sur "Sign up"
3. Crée ton compte gratuit

### Minute 2 : Push le code sur GitHub

Ouvre ton terminal et tape :

```bash
cd /workspace/ivoircyberscan

# Initialise git
git init

# Ajoute tous les fichiers
git add .

# Commit
git commit -m "🇨🇮 IvoirCyberScan V1 - Prêt à déployer"

# Crée la branche main
git branch -M main

# Crée un nouveau repository sur GitHub (remplace TON_USERNAME par ton pseudo)
# VA SUR : https://github.com/new
# Nom du repo : ivoircyberscan
# Puis copie l'URL et exécute :
git remote add origin https://github.com/TON_USERNAME/ivoircyberscan.git

# Push vers GitHub
git push -u origin main
```

### Minute 3-4 : Déployer sur Vercel

1. **Va sur https://vercel.com**
2. **Clique sur "Sign Up"** → Connecte-toi avec GitHub
3. **Clique sur "Add New Project"**
4. **Trouve `ivoircyberscan`** dans la liste et clique sur "Import"
5. **Laisse les settings par défaut :**
   - Framework Preset: Next.js ✅
   - Root Directory: ./ ✅
   - Build Command: `npm run build` ✅
6. **Clique sur "Deploy"** 🚀

### Minute 5 : C'est en ligne ! 🎉

Vercel va te donner une URL du type :
```
https://ivoircyberscan-xxxx.vercel.app
```

**Ton site est maintenant accessible dans le monde entier !**

---

## 💳 CONFIGURER LES PAIEMENTS

### Option 1 : Stripe (Recommandé pour cartes bancaires)

1. **Crée ton compte Stripe** → https://stripe.com
2. **Récupère ta clé secrète** dans Dashboard → Developers → API keys
3. **Dans Vercel, va dans :** Settings → Environment Variables
4. **Ajoute :**
   ```
   STRIPE_SECRET_KEY = sk_test_xxxxxxxxxxxxxx
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY = pk_test_xxxxxxxxxxxxxx
   ```
5. **Redéploie ton site** (Deployments → ... → Redeploy)

### Option 2 : WhatsApp (Le plus simple pour commencer)

Tes boutons de paiement redirigent déjà vers WhatsApp !

Quand un client clique sur "Payer avec Orange Money", il ouvre WhatsApp avec ce message pré-rempli :
```
Salut ! Je veux m'abonner à IvoirCyberScan Premium (9 900 FCFA/mois). Comment procéder au paiement ?
```

**Toi tu reçois le message** et tu guides le client :
1. Il paie par Wave/Orange Money/MTN
2. Il t'envoie la preuve de paiement
3. Tu lui envoies le rapport PDF complet manuellement
4. Tu notes son email dans un Google Sheet pour le suivi

### Option 3 : Stripe + WhatsApp (Hybride)

Pour activer Stripe tout en gardant WhatsApp comme backup :

1. Dans Vercel → Settings → Environment Variables, ajoute :
   ```
   STRIPE_SECRET_KEY = sk_live_xxxxxxxxxxxxxx (clé réelle, pas test)
   NEXT_PUBLIC_URL = https://ton-domaine.vercel.app
   NEXT_PUBLIC_WHATSAPP_NUMBER = 2250707070707
   ```

2. Le code détectera automatiquement si Stripe est configuré et l'utilisera en priorité.

---

## 📱 PERSONNALISATION

### Changer le numéro WhatsApp

Dans Vercel → Settings → Environment Variables :
```
NEXT_PUBLIC_WHATSAPP_NUMBER = 225XXXXXXXX
```

### Changer les prix

```
NEXT_PUBLIC_PRICING_MONTHLY = 9900
NEXT_PUBLIC_PRICING_YEARLY = 99000
```

### Ajouter ton propre domaine

1. Achète un domaine (ex: `ivoircyberscan.ci`) chez LWS ou GoDaddy
2. Dans Vercel → Settings → Domains → Add Domain
3. Suis les instructions pour configurer tes DNS
4. Attends 24h que la propagation DNS se fasse

---

## 🔧 MAINTENANCE

### Mettre à jour le site

```bash
# Fais tes modifications locales
git add .
git commit -m "Update"
git push
```

Vercel va automatiquement redéployer !

### Voir les logs

Dans Vercel Dashboard → Ton projet → Logs

### Analytics (gratuit)

1. Va sur https://vercel.com/analytics
2. Active Vercel Analytics sur ton projet
3. Tu verras combien de personnes visitent ton site

---

## 🆘 SUPPORT & QUESTIONS FRÉQUENTES

**Q: Mon site ne se déploie pas ?**
R: Vérifie les logs dans Vercel. Souvent c'est une erreur TypeScript. Corrige et push à nouveau.

**Q: Comment générer les rapports PDF ?**
R: En V1, tu les génères manuellement avec Canva ou Google Docs. En V2, on ajoutera la génération automatique.

**Q: Combien ça coûte d'héberger sur Vercel ?**
R: Gratuit ! Le plan Hobby inclut :
- 100GB de bande passante/mois
- Sites illimités
- SSL gratuit
- Déploiements automatiques

**Q: Comment recevoir les paiements sur mon compte ?**
R: 
- Stripe : Virement automatique sur ton compte bancaire chaque semaine
- Wave/Orange Money : Directement sur ton compte mobile money

**Q: Puis-je avoir plusieurs comptes utilisateurs ?**
R: En V1, non. En V2, on ajoutera Supabase pour gérer les comptes.

---

## 📞 CONTACT URGENCE

Si tu es bloqué :
- WhatsApp : +225 07 07 07 07 07
- Email : support@ivoircyberscan.ci

**Bon courage champion ! 🇨🇮💪**

Ton outil va protéger des centaines de business ivoiriens contre les brouteurs !
