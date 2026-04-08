import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "IvoirCyberScan - Protège ton business contre les brouteurs",
  description: "Scanner de vulnérabilités IA ultra-simple pour PME ivoiriennes. Protège ton business contre les brouteurs, le phishing et les ransomware en 2 minutes.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
