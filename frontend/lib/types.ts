export type Citation = {
  etiquette: string;
  chunk_id: string;
  source_titre: string;
  identifiant: string;
  reference: string;
  texte: string;
  url: string;
  version: string;
  date_consultation: string;
  contraignant: string;
};

export type Reponse = {
  decision: "repondre" | "refuser";
  motif: string | null;
  couche_refus: string | null;
  reponse: string;
  citations: Citation[];
  avertissement: string;
};

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const LIBELLES_MOTIF: Record<string, string> = {
  hors_corpus: "Hors du corpus",
  passages_insuffisants: "Passages insuffisants",
  avis_juridique: "Pas d'avis sur un cas particulier",
  echec_format: "Réponse non fournie (contrôle de sécurité)",
  echec_verification: "Réponse non fournie (contrôle de sécurité)",
  echec_technique: "Réponse non fournie (contrôle de sécurité)",
};
