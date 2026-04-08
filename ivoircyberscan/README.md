# 🇨🇮 IvoirCyberScan - Scanner de Vulnérabilités IA pour PME Ivoiriennes

**Protège ton business contre les brouteurs, le phishing et les ransomware en 2 minutes**

## 🚀 Déploiement sur Vercel en 5 minutes

### Étape 1 : Préparer ton projet

1. **Crée un compte GitHub** (si tu n'en as pas) sur [github.com](https://github.com)

2. **Push ton code sur GitHub :**
```bash
cd /workspace/ivoircyberscan
git init
git add .
git commit -m "Initial commit IvoirCyberScan V1"
git branch -M main
git remote add origin https://github.com/TON_USERNAME/ivoircyberscan.git
git push -u origin main
```

### Étape 2 : Déployer sur Vercel

1. **Va sur [vercel.com](https://vercel.com)** et crée un compte gratuit

2. **Clique sur "Add New Project"**

3. **Importe ton repository GitHub** `ivoircyberscan`

4. **Configure le projet :**
   - Framework Preset: **Next.js** (auto-détecté)
   - Root Directory: `./` (laisse par défaut)
   - Build Command: `npm run build`
   - Output Directory: `.next`

5. **Clique sur "Deploy"** 🎉

6. **Attends 2-3 minutes** et ton site est en ligne !

### Étape 3 : Personnaliser le domaine (optionnel)

1. Dans ton dashboard Vercel, va dans **Settings → Domains**

2. Ajoute ton domaine personnalisé (ex: `ivoircyberscan.ci`)

3. Suis les instructions pour configurer tes DNS

---

## 💳 Ajouter les Paiements (Stripe, Wave, Orange Money)

### Option 1 : Stripe (Cartes Bancaires)

1. **Crée un compte Stripe** sur [stripe.com](https://stripe.com)

2. **Récupère ta clé API** dans le dashboard Stripe

3. **Installe Stripe dans ton projet :**
```bash
npm install @stripe/stripe-js
```

4. **Crée une API Route** `/src/app/api/create-checkout/route.ts` :
```typescript
import { NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST() {
  const session = await stripe.checkout.sessions.create({
    payment_method_types: ['card'],
    line_items: [{
      price_data: {
        currency: 'eur',
        product_data: { name: 'IvoirCyberScan Premium' },
        unit_amount: 9900 * 100, // 9900 FCFA en centimes
      },
      quantity: 1,
    }],
    mode: 'subscription',
    success_url: `${process.env.NEXT_PUBLIC_URL}/success`,
    cancel_url: `${process.env.NEXT_PUBLIC_URL}/cancel`,
  });

  return NextResponse.json({ url: session.url });
}
```

5. **Ajoute tes variables d'environnement** dans Vercel :
   - `STRIPE_SECRET_KEY`
   - `NEXT_PUBLIC_URL`

### Option 2 : Wave (Côte d'Ivoire)

1. **Contacte Wave Business** : business@wave.com

2. **Utilise leur API de paiement** (documentation sur demande)

3. **Alternative simple** : Génère un lien de paiement manuel
   - Crée un bouton WhatsApp qui redirige vers ton numéro
   - Le client paie via l'app Wave et t'envoie la preuve
   - Tu actives manuellement son abonnement

### Option 3 : Orange Money

1. **Inscris-toi sur [Orange Business CI](https://business.orange.ci)**

2. **Demande l'accès à l'API Orange Money**

3. **Intègre le widget de paiement** dans ton site

### Option 4 : Solution Simple (Recommandée pour débuter)

Crée un formulaire WhatsApp automatique :

```typescript
// Quand le client clique sur "Payer avec Orange Money"
const payerAvecOrangeMoney = () => {
  const message = encodeURIComponent(
    "Salut ! Je veux m'abonner à IvoirCyberScan Premium (9 900 FCFA/mois). " +
    "Comment procéder au paiement par Orange Money ?"
  );
  window.open(`https://wa.me/2250707070707?text=${message}`, '_blank');
};
```

---

## 🔧 Améliorations Futures (V2)

### Intégration IA Réelle

1. **Nuclei Scan** (gratuit) :
```bash
# Installe Nuclei
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Scan une URL
nuclei -u https://cible.com -t vulnerabilities/
```

2. **API Claude/Grok** :
```typescript
// Appelle l'API Anthropic pour analyser les résultats
const response = await fetch('https://api.anthropic.com/v1/messages', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${process.env.ANTHROPIC_API_KEY}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1024,
    messages: [{
      role: 'user',
      content: `Analyse ces vulnérabilités et génère un rapport en français ivoirien : ${scanResults}`
    }]
  })
});
```

3. **OWASP ZAP** (via API) :
   - Héberge ZAP sur un serveur gratuit (Render, Railway)
   - Appelle l'API depuis ton backend Next.js

### Génération PDF

```bash
npm install @react-pdf/renderer
```

Crée un composant PDF qui génère le rapport complet.

---

## 📊 Architecture Actuelle (V1)

```
IvoirCyberScan V1
├── Frontend : Next.js 14 + Tailwind CSS
├── Analyse : Simulation IA (mock data)
├── Hébergement : Vercel (gratuit)
├── Base de données : Local Storage (temporaire)
└── Paiement : Boutons vers WhatsApp/Stripe
```

---

## 🎨 Couleurs Côte d'Ivoire

- **Vert** : `#00A651`
- **Orange** : `#FF8200`
- **Blanc** : `#FFFFFF`

---

## 📞 Support

Pour toute question ou amélioration :
- Email : contact@ivoircyberscan.ci
- WhatsApp : +225 07 07 07 07 07

**Fait avec ❤️ à Abidjan pour les PME ivoiriennes**

---

## Licence

MIT License - Gratuit pour usage commercial
