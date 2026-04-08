import { NextResponse } from 'next/server';

/**
 * API Route pour créer une session de paiement Stripe
 * 
 * Utilisation en V2 - Pour l'instant, cette route est en attente
 * Configure tes clés Stripe dans .env.local avant d'activer
 */

export async function POST(request: Request) {
  try {
    // Vérifie si Stripe est configuré
    if (!process.env.STRIPE_SECRET_KEY) {
      return NextResponse.json(
        { 
          error: 'Stripe non configuré',
          message: 'Configure STRIPE_SECRET_KEY dans tes variables d\'environnement',
          fallback: {
            whatsapp: `https://wa.me/${process.env.NEXT_PUBLIC_WHATSAPP_NUMBER || '2250707070707'}?text=${encodeURIComponent('Salut ! Je veux m\'abonner à IvoirCyberScan Premium (9 900 FCFA/mois). Comment procéder au paiement ?')}`
          }
        },
        { status: 200 }
      );
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const body = await request.json();
    
    // Note: Stripe SDK sera installé en V2
    // Pour l'instant, on retourne un lien WhatsApp comme fallback
    
    return NextResponse.json({
      url: `https://wa.me/${process.env.NEXT_PUBLIC_WHATSAPP_NUMBER || '2250707070707'}?text=${encodeURIComponent('Salut ! Je veux m\'abonner à IvoirCyberScan Premium. Voici les options de paiement disponibles :\n\n💳 Carte Bancaire (Stripe)\n📱 Wave\n📱 Orange Money\n📱 MTN Mobile Money\n\nMerci de me guider pour le paiement.')}`,
      message: 'Redirection vers WhatsApp pour finaliser le paiement',
      pricing: {
        monthly: `${process.env.NEXT_PUBLIC_PRICING_MONTHLY || 9900} FCFA/mois`,
        yearly: `${process.env.NEXT_PUBLIC_PRICING_YEARLY || 99000} FCFA/an (2 mois offerts!)`
      }
    });
    
  } catch (error) {
    console.error('Erreur création session paiement:', error);
    return NextResponse.json(
      { 
        error: 'Erreur serveur',
        fallback: `https://wa.me/${process.env.NEXT_PUBLIC_WHATSAPP_NUMBER || '2250707070707'}`
      },
      { status: 500 }
    );
  }
}

// GET endpoint pour tester la configuration
export async function GET() {
  return NextResponse.json({
    status: 'ok',
    stripeConfigured: !!process.env.STRIPE_SECRET_KEY,
    whatsappNumber: process.env.NEXT_PUBLIC_WHATSAPP_NUMBER || '2250707070707',
    pricing: {
      monthly: `${process.env.NEXT_PUBLIC_PRICING_MONTHLY || 9900} FCFA`,
      yearly: `${process.env.NEXT_PUBLIC_PRICING_YEARLY || 99000} FCFA`
    },
    instructions: {
      stripe: 'Pour activer Stripe : 1) Crée un compte sur stripe.com 2) Ajoute STRIPE_SECRET_KEY dans .env.local 3) npm install stripe',
      wave: 'Contacte business@wave.com pour l\'API Wave',
      orangeMoney: 'Inscris-toi sur business.orange.ci pour l\'API Orange Money',
      mtn: 'Contacte mtnbusiness.ci pour MTN Mobile Money'
    }
  });
}
