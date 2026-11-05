import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Veille MiCA : assistant de veille réglementaire crypto-actifs",
  description: "Recherche dans des textes officiels (MiCA et textes liés), avec citation du passage exact. Ceci n'est pas un conseil juridique.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <div className="avertissement" role="note">
          <div className="conteneur">
            <strong>Ceci n'est pas un conseil juridique.</strong> Cet outil retrouve des passages de textes officiels ; il ne
            qualifie aucune situation particulière.
          </div>
        </div>
        {children}
      </body>
    </html>
  );
}
