import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

// Polices auto-hébergées (licence SIL OFL 1.1), servies depuis le dépôt : aucun appel à un CDN.
const serif = localFont({
  src: [
    { path: "../node_modules/@fontsource-variable/source-serif-4/files/source-serif-4-latin-wght-normal.woff2", style: "normal" },
    { path: "../node_modules/@fontsource-variable/source-serif-4/files/source-serif-4-latin-wght-italic.woff2", style: "italic" },
  ],
  variable: "--police-serif",
  display: "swap",
});
const sans = localFont({
  src: [
    { path: "../node_modules/@fontsource-variable/source-sans-3/files/source-sans-3-latin-wght-normal.woff2", style: "normal" },
    { path: "../node_modules/@fontsource-variable/source-sans-3/files/source-sans-3-latin-wght-italic.woff2", style: "italic" },
  ],
  variable: "--police-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Veille MiCA : veille réglementaire sur les crypto-actifs",
  description: "Recherche dans des textes officiels (MiCA et textes liés), avec citation du passage exact. Ceci n'est pas un conseil juridique.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${serif.variable} ${sans.variable}`}>
      <body>
        <div className="avertissement" role="note">
          <div className="colonne">
            <strong>Ceci n'est pas un conseil juridique.</strong> Cet outil retrouve des passages de textes officiels ; il ne
            qualifie aucune situation particulière.
          </div>
        </div>
        {children}
      </body>
    </html>
  );
}
