'use client';

import { useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, Lock, Smartphone, Mail, Globe, Download, CreditCard } from 'lucide-react';

interface ScanResult {
  input: string;
  inputType: 'url' | 'email' | 'whatsapp';
  riskLevel: 'faible' | 'moyen' | 'élevé' | 'critique';
  riskScore: number;
  potentialLoss: string;
  vulnerabilities: Vulnerability[];
  antiBrouteurChecklist: string[];
  fixes: string[];
  timestamp: string;
}

interface Vulnerability {
  name: string;
  severity: 'faible' | 'moyen' | 'élevé' | 'critique';
  description: string;
  recommendation: string;
}

export default function Home() {
  const [inputValue, setInputValue] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [showPremium, setShowPremium] = useState(false);

  const detectInputType = (value: string): 'url' | 'email' | 'whatsapp' => {
    if (value.includes('@')) return 'email';
    if (value.includes('wa.me') || value.includes('whatsapp.com') || value.startsWith('+')) return 'whatsapp';
    return 'url';
  };

  const generateMockAnalysis = (input: string, type: 'url' | 'email' | 'whatsapp'): ScanResult => {
    // Simulation d'analyse IA - dans la version finale, ceci appellera une vraie API
    const mockVulnerabilities: Vulnerability[] = [];
    const mockChecklist: string[] = [];
    const mockFixes: string[] = [];
    
    let riskLevel: 'faible' | 'moyen' | 'élevé' | 'critique' = 'moyen';
    let riskScore = 50;
    let potentialLoss = '500 000 FCFA';

    if (type === 'url') {
      mockVulnerabilities.push(
        {
          name: 'SSL/TLS Non Configuré',
          severity: 'élevé',
          description: 'Ton site n\'utilise pas HTTPS. Les données de tes clients peuvent être interceptées.',
          recommendation: 'Installe un certificat SSL gratuit avec Let\'s Encrypt.'
        },
        {
          name: 'En-têtes de Sécurité Manquants',
          severity: 'moyen',
          description: 'Les en-têtes X-Frame-Options et CSP ne sont pas configurés.',
          recommendation: 'Configure les en-têtes de sécurité dans ton serveur web.'
        },
        {
          name: 'Version WordPress Obsolète',
          severity: 'élevé',
          description: 'Détection d\'une version ancienne de WordPress avec des failles connues.',
          recommendation: 'Mets à jour WordPress et tous tes plugins immédiatement.'
        }
      );
      
      mockChecklist.push(
        '⚠️ Vérifie que ton site affiche bien le cadenas vert (HTTPS)',
        '📱 Ne clique jamais sur les liens suspects dans les emails',
        '💰 Active la double authentification sur ton compte Orange Money / MTN Mobile Money',
        '🔒 Change tes mots de passe tous les 3 mois'
      );
      
      mockFixes.push(
        '1. Connecte-toi à ton hébergeur (LWS, Hostinger, etc.)',
        '2. Active le certificat SSL gratuit dans le panneau de contrôle',
        '3. Mets à jour WordPress : Tableau de bord → Mises à jour',
        '4. Installe le plugin Wordfence pour la protection firewall',
        '5. Configure la sauvegarde automatique hebdomadaire'
      );
      
      riskLevel = 'élevé';
      riskScore = 75;
      potentialLoss = '2 500 000 FCFA';
    } else if (type === 'email') {
      mockVulnerabilities.push(
        {
          name: 'Risque de Phishing Élevé',
          severity: 'critique',
          description: 'Cet email professionnel peut être facilement imité par des brouteurs.',
          recommendation: 'Configure SPF, DKIM et DMARC pour authentifier tes emails.'
        },
        {
          name: 'Absence de Signature Email Sécurisée',
          severity: 'moyen',
          description: 'Tes emails n\'ont pas de signature vérifiable.',
          recommendation: 'Ajoute une signature professionnelle avec tes coordonnées officielles.'
        }
      );
      
      mockChecklist.push(
        '⚠️ Méfie-toi des emails qui demandent de l\'argent urgent',
        '📞 Vérifie toujours par téléphone avant un virement Mobile Money',
        '🔐 Utilise un mot de passe fort (12 caractères minimum)',
        '👀 Regarde bien l\'adresse de l\'expéditeur (ex: @orange.ci vs @orange-cl.com)'
      );
      
      mockFixes.push(
        '1. Contacte ton fournisseur d\'hébergement email',
        '2. Demande la configuration SPF et DKIM',
        '3. Ajoute un enregistrement DMARC dans tes DNS',
        '4. Forme ton équipe à reconnaître les emails de phishing',
        '5. Mets en place une procédure de validation des virements'
      );
      
      riskLevel = 'critique';
      riskScore = 85;
      potentialLoss = '5 000 000 FCFA';
    } else {
      mockVulnerabilities.push(
        {
          name: 'Numéro WhatsApp Business Exposé',
          severity: 'moyen',
          description: 'Ton numéro WhatsApp Business est public et peut être ciblé par des brouteurs.',
          recommendation: 'Limite la visibilité de ton numéro et utilise uniquement pour le business.'
        },
        {
          name: 'Absence de Verification Badge',
          severity: 'faible',
          description: 'Ton compte WhatsApp Business n\'est pas vérifié.',
          recommendation: 'Demande la vérification officielle auprès de Meta.'
        }
      );
      
      mockChecklist.push(
        '⚠️ Ne partage jamais ton code de validation WhatsApp',
        '💰 Confirme toujours les paiements par un autre canal',
        '🚫 Bloque immédiatement les numéros suspects (+225 avec offre trop belle)',
        '📸 Active la validation en deux étapes dans WhatsApp'
      );
      
      mockFixes.push(
        '1. Ouvre WhatsApp Business → Paramètres → Confidentialité',
        '2. Limite ta photo de profil à "Mes contacts" seulement',
        '3. Active la validation en deux étapes',
        '4. Crée un catalogue professionnel pour éviter les arnaques',
        '5. Forme ton équipe : ne jamais envoyer d\'argent sans confirmation téléphonique'
      );
      
      riskLevel = 'moyen';
      riskScore = 45;
      potentialLoss = '1 000 000 FCFA';
    }

    return {
      input,
      inputType: type,
      riskLevel,
      riskScore,
      potentialLoss,
      vulnerabilities: mockVulnerabilities,
      antiBrouteurChecklist: mockChecklist,
      fixes: mockFixes,
      timestamp: new Date().toLocaleString('fr-FR')
    };
  };

  const handleScan = async () => {
    if (!inputValue.trim()) return;
    
    setIsScanning(true);
    setScanResult(null);
    
    // Simulation de délai d'analyse (dans la version finale, appel API réel)
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const inputType = detectInputType(inputValue);
    const result = generateMockAnalysis(inputValue, inputType);
    
    setScanResult(result);
    setIsScanning(false);
  };

  const getRiskColor = (level: string) => {
    switch(level) {
      case 'faible': return 'text-green-600 bg-green-100';
      case 'moyen': return 'text-orange-600 bg-orange-100';
      case 'élevé': return 'text-red-600 bg-red-100';
      case 'critique': return 'text-red-800 bg-red-200';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch(severity) {
      case 'faible': return 'border-green-500 text-green-700';
      case 'moyen': return 'border-orange-500 text-orange-700';
      case 'élevé': return 'border-red-500 text-red-700';
      case 'critique': return 'border-red-700 text-red-900 bg-red-50';
      default: return 'border-gray-500 text-gray-700';
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-white to-orange-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-[#00A651] via-white to-[#FF8200] py-6 px-4 shadow-lg">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Shield className="w-10 h-10 text-white drop-shadow-md" />
            <div>
              <h1 className="text-2xl font-bold text-white drop-shadow-md">IvoirCyberScan</h1>
              <p className="text-sm text-gray-700 font-medium">🇨🇮 Protège ton business contre les brouteurs</p>
            </div>
          </div>
          <div className="hidden md:block text-right">
            <p className="text-xs text-gray-700">Fait avec ❤️ à Abidjan</p>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-12 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-block bg-white rounded-full px-6 py-2 shadow-md mb-6">
            <span className="text-sm font-semibold text-gray-700">
              🛡️ Scanner de vulnérabilités IA pour PME ivoiriennes
            </span>
          </div>
          
          <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
            Protège ton business contre les{' '}
            <span className="ci-orange-bg text-white px-2 rounded">brouteurs</span>,{' '}
            <span className="ci-green-bg text-white px-2 rounded">phishing</span> et{' '}
            <span className="bg-red-600 text-white px-2 rounded">ransomware</span>{' '}
            en 2 minutes
          </h2>
          
          <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
            Analyse gratuite de ton site web, email pro ou WhatsApp Business. 
            Reçois un rapport clair avec les failles de sécurité et comment les corriger.
          </p>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mb-8 max-w-2xl mx-auto">
            <div className="bg-white rounded-lg p-4 shadow-md">
              <p className="text-2xl font-bold ci-orange">2 500+</p>
              <p className="text-xs text-gray-600">Business protégés</p>
            </div>
            <div className="bg-white rounded-lg p-4 shadow-md">
              <p className="text-2xl font-bold ci-green">98%</p>
              <p className="text-xs text-gray-600">Taux de satisfaction</p>
            </div>
            <div className="bg-white rounded-lg p-4 shadow-md">
              <p className="text-2xl font-bold text-red-600">15M FCFA</p>
              <p className="text-xs text-gray-600">Économisés en 2024</p>
            </div>
          </div>
        </div>
      </section>

      {/* Scan Form */}
      <section className="py-8 px-4">
        <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-xl p-8">
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            🔍 Commence ton scan gratuit
          </h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Colle ton URL, email pro ou lien WhatsApp Business
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Ex: https://monsite.ci / contact@entreprise.ci / +225 07 07 07 07 07"
                  className="w-full px-4 py-4 border-2 border-gray-300 rounded-xl focus:border-[#00A651] focus:ring-2 focus:ring-green-200 outline-none transition-all text-lg"
                  onKeyPress={(e) => e.key === 'Enter' && handleScan()}
                />
                {inputValue && (
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                    {detectInputType(inputValue) === 'url' && <Globe className="w-6 h-6 text-gray-400" />}
                    {detectInputType(inputValue) === 'email' && <Mail className="w-6 h-6 text-gray-400" />}
                    {detectInputType(inputValue) === 'whatsapp' && <Smartphone className="w-6 h-6 text-gray-400" />}
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={handleScan}
              disabled={isScanning || !inputValue.trim()}
              className={`w-full py-4 rounded-xl font-bold text-lg transition-all ${
                isScanning || !inputValue.trim()
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-[#00A651] to-[#FF8200] text-white hover:shadow-lg hover:scale-105'
              }`}
            >
              {isScanning ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Analyse en cours...
                </span>
              ) : (
                '🚀 Lancer le scan gratuit'
              )}
            </button>

            <p className="text-xs text-gray-500 text-center">
              🔒 Tes données sont sécurisées et supprimées après 24h. Scan 100% gratuit.
            </p>
          </div>
        </div>
      </section>

      {/* Results Section */}
      {scanResult && (
        <section className="py-12 px-4">
          <div className="max-w-4xl mx-auto space-y-8">
            {/* Risk Summary */}
            <div className="bg-white rounded-2xl shadow-xl p-8">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-2xl font-bold text-gray-900">📊 Résultat du scan</h3>
                <span className={`px-4 py-2 rounded-full font-bold ${getRiskColor(scanResult.riskLevel)}`}>
                  Risque {scanResult.riskLevel.toUpperCase()}
                </span>
              </div>

              <div className="grid md:grid-cols-3 gap-6 mb-6">
                <div className="bg-red-50 rounded-xl p-6 text-center">
                  <AlertTriangle className="w-12 h-12 text-red-600 mx-auto mb-3" />
                  <p className="text-3xl font-bold text-red-700">{scanResult.riskScore}/100</p>
                  <p className="text-sm text-gray-600">Score de risque</p>
                </div>
                <div className="bg-orange-50 rounded-xl p-6 text-center">
                  <Lock className="w-12 h-12 text-orange-600 mx-auto mb-3" />
                  <p className="text-3xl font-bold text-orange-700">{scanResult.vulnerabilities.length}</p>
                  <p className="text-sm text-gray-600">Failles détectées</p>
                </div>
                <div className="bg-red-100 rounded-xl p-6 text-center">
                  <CreditCard className="w-12 h-12 text-red-600 mx-auto mb-3" />
                  <p className="text-xl font-bold text-red-700">{scanResult.potentialLoss}</p>
                  <p className="text-sm text-gray-600">Perte potentielle si attaqué</p>
                </div>
              </div>

              <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded">
                <p className="text-yellow-800 font-medium">
                  ⚠️ Attention ! {scanResult.potentialLoss} pourraient être perdus si des cybercriminels exploitent ces failles. 
                  Agis maintenant pour protéger ton business.
                </p>
              </div>
            </div>

            {/* Vulnerabilities */}
            <div className="bg-white rounded-2xl shadow-xl p-8">
              <h3 className="text-2xl font-bold text-gray-900 mb-6">🔴 Failles de sécurité détectées</h3>
              <div className="space-y-4">
                {scanResult.vulnerabilities.map((vuln, index) => (
                  <div key={index} className={`border-l-4 p-4 rounded-r-lg ${getSeverityColor(vuln.severity)}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-bold text-lg">{vuln.name}</h4>
                        <p className="text-sm mt-1 opacity-80">{vuln.description}</p>
                        <p className="text-sm mt-2 font-semibold">💡 Solution : {vuln.recommendation}</p>
                      </div>
                      <span className="px-3 py-1 rounded-full text-xs font-bold bg-white shadow">
                        {vuln.severity.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Anti-Brouteurs Checklist */}
            <div className="bg-gradient-to-br from-[#00A651] to-green-600 rounded-2xl shadow-xl p-8 text-white">
              <h3 className="text-2xl font-bold mb-6">🛡️ Checklist Anti-Brouteurs</h3>
              <div className="space-y-3">
                {scanResult.antiBrouteurChecklist.map((item, index) => (
                  <div key={index} className="flex items-start space-x-3">
                    <CheckCircle className="w-6 h-6 flex-shrink-0 mt-0.5" />
                    <p className="font-medium">{item}</p>
                  </div>
                ))}
              </div>
              
              <div className="mt-6 bg-white/20 rounded-lg p-4">
                <p className="font-semibold">💰 Comment sécuriser ton Mobile Money / Orange Money :</p>
                <ul className="mt-2 space-y-1 text-sm">
                  <li>• Active le code secret à 4 chiffres</li>
                  <li>• Ne partage JAMAIS ton code PIN</li>
                  <li>• Vérifie le numéro avant chaque envoi</li>
                  <li>• Active les notifications SMS pour chaque transaction</li>
                  <li>• En cas de doute, appelle le service client (#155 pour Orange, #175 pour MTN)</li>
                </ul>
              </div>
            </div>

            {/* Fixes Step by Step */}
            <div className="bg-white rounded-2xl shadow-xl p-8">
              <h3 className="text-2xl font-bold text-gray-900 mb-6">🔧 Fixes concrets étape par étape</h3>
              <div className="space-y-4">
                {scanResult.fixes.map((fix, index) => (
                  <div key={index} className="flex items-start space-x-4">
                    <div className="w-8 h-8 rounded-full ci-orange-bg text-white flex items-center justify-center font-bold flex-shrink-0">
                      {index + 1}
                    </div>
                    <p className="pt-1 font-medium text-gray-800">{fix}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* CTA Premium */}
            <div className="bg-gradient-to-r from-gray-900 to-gray-800 rounded-2xl shadow-xl p-8 text-white text-center">
              <h3 className="text-2xl font-bold mb-4">📄 Obtenir le rapport complet en PDF</h3>
              <p className="mb-6 text-gray-300">
                Le rapport gratuit te donne les principales failles. Passe à la version premium pour avoir :
              </p>
              <ul className="text-left max-w-md mx-auto space-y-2 mb-6 text-gray-300">
                <li>✅ Rapport PDF complet et détaillé</li>
                <li>✅ Audit de sécurité approfondi</li>
                <li>✅ Assistance prioritaire par WhatsApp</li>
                <li>✅ Scans illimités chaque mois</li>
                <li>✅ Alertes en temps réel en cas de nouvelle menace</li>
              </ul>
              
              {!showPremium ? (
                <button
                  onClick={() => setShowPremium(true)}
                  className="bg-gradient-to-r from-[#FF8200] to-orange-600 text-white px-8 py-4 rounded-xl font-bold text-lg hover:shadow-lg hover:scale-105 transition-all"
                >
                  Voir les options de paiement
                </button>
              ) : (
                <div className="space-y-4">
                  <div className="bg-white/10 rounded-xl p-6">
                    <p className="text-3xl font-bold mb-2">9 900 FCFA<span className="text-base font-normal text-gray-300">/mois</span></p>
                    <p className="text-sm text-gray-300 mb-4">ou 99 000 FCFA/an (économise 2 mois!)</p>
                    
                    <div className="space-y-3">
                      <button className="w-full bg-[#FF8200] text-white py-3 rounded-lg font-bold hover:bg-orange-600 transition-colors">
                        💳 Payer avec Carte Bancaire (Stripe)
                      </button>
                      <button className="w-full bg-[#FF6600] text-white py-3 rounded-lg font-bold hover:bg-orange-700 transition-colors">
                        📱 Payer avec Wave
                      </button>
                      <button className="w-full bg-[#FF7900] text-white py-3 rounded-lg font-bold hover:bg-orange-700 transition-colors">
                        📱 Payer avec Orange Money
                      </button>
                      <button className="w-full bg-[#FFCC00] text-black py-3 rounded-lg font-bold hover:bg-yellow-500 transition-colors">
                        📱 Payer avec MTN Mobile Money
                      </button>
                    </div>
                    
                    <p className="text-xs text-gray-400 mt-4">
                      🔒 Paiement sécurisé. Annulable à tout moment.
                    </p>
                  </div>
                  
                  <button
                    onClick={() => setShowPremium(false)}
                    className="text-gray-400 text-sm hover:text-white"
                  >
                    Retour au résumé gratuit
                  </button>
                </div>
              )}
            </div>

            {/* Timestamp */}
            <p className="text-center text-sm text-gray-500">
              Scan effectué le {scanResult.timestamp} • Données conservées 24h
            </p>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12 px-4 mt-12">
        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8 mb-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Shield className="w-8 h-8" />
                <h4 className="text-xl font-bold">IvoirCyberScan</h4>
              </div>
              <p className="text-gray-400 text-sm">
                Premier scanner de vulnérabilités IA conçu spécialement pour les PME ivoiriennes. 
                Fait avec ❤️ à Abidjan.
              </p>
            </div>
            
            <div>
              <h5 className="font-bold mb-4">Liens utiles</h5>
              <ul className="space-y-2 text-gray-400 text-sm">
                <li><a href="#" className="hover:text-white">Comment ça marche</a></li>
                <li><a href="#" className="hover:text-white">Tarifs</a></li>
                <li><a href="#" className="hover:text-white">Blog cybersécurité</a></li>
                <li><a href="#" className="hover:text-white">Contact</a></li>
              </ul>
            </div>
            
            <div>
              <h5 className="font-bold mb-4">Urgence Cyber</h5>
              <p className="text-gray-400 text-sm mb-2">
                Victime d'une cyberattaque ?
              </p>
              <p className="text-2xl font-bold ci-orange">📞 +225 07 07 07 07 07</p>
              <p className="text-xs text-gray-500 mt-2">
                Support disponible 24/7 sur WhatsApp
              </p>
            </div>
          </div>
          
          <div className="border-t border-gray-800 pt-8 text-center text-gray-500 text-sm">
            <p>© 2024 IvoirCyberScan. Tous droits réservés. 🇨🇮</p>
            <p className="mt-2">
              <a href="#" className="hover:text-white">Mentions légales</a> • 
              <a href="#" className="hover:text-white">Politique de confidentialité</a> • 
              <a href="#" className="hover:text-white">CGV</a>
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}
