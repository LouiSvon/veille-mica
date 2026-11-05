"use client";

import { FormEvent, useEffect, useState } from "react";
import { API_URL, LIBELLES_MOTIF, type Citation, type Reponse } from "../lib/types";

const EXEMPLES = [
  "Jusqu'à quand les prestataires qui fournissaient déjà leurs services avant le 30 décembre 2024 peuvent-ils continuer sans agrément MiCA ?",
  "Comment MiCA définit-il un crypto-actif ?",
  "À partir de quelle date les orientations de l'ABE sur la travel rule s'appliquent-elles ?",
];

const CORPUS = [
  "Règlement (UE) 2023/1114 sur les marchés de crypto-actifs (MiCA)",
  "Règlement (UE) 2023/1113 sur les transferts de fonds et de certains crypto-actifs",
  "Orientations de l'ABE",
  "Position de l'AMF",
  "Ordonnance n° 2024-936 du 15 octobre 2024",
];

class ErreurApi extends Error {}

function texteCitation(c: Citation): string {
  const statut = c.contraignant === "oui" ? "" : c.contraignant === "non" ? " (non contraignant)" : " (statut non vérifié)";
  return `« ${c.texte.trim()} »\n${c.reference}, ${c.source_titre}${statut}\n${c.identifiant}, version : ${c.version}, consulté le ${c.date_consultation}\n${c.url}`;
}

function BoutonCopier({ texte, libelle }: { texte: string; libelle: string }) {
  const [etat, setEtat] = useState<"" | "ok" | "echec">("");
  async function copier() {
    try {
      await navigator.clipboard.writeText(texte);
      setEtat("ok");
    } catch {
      setEtat("echec");
    }
    setTimeout(() => setEtat(""), 2000);
  }
  return (
    <button type="button" className="lien-bouton" onClick={copier}>
      {etat === "ok" ? "Copié" : etat === "echec" ? "Copie impossible" : libelle}
    </button>
  );
}

export default function Page() {
  const [question, setQuestion] = useState("");
  const [reponse, setReponse] = useState<Reponse | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  // À l'impression, toutes les citations sont dépliées pour que les sources figurent sur le papier.
  useEffect(() => {
    const ouvrir = () => document.querySelectorAll("details").forEach((d) => { d.open = true; });
    window.addEventListener("beforeprint", ouvrir);
    return () => window.removeEventListener("beforeprint", ouvrir);
  }, []);

  async function poser(e?: FormEvent, texte?: string) {
    e?.preventDefault();
    const q = (texte ?? question).trim();
    if (q.length < 3) {
      setErreur("Écrivez une question d'au moins 3 caractères.");
      return;
    }
    setEnCours(true);
    setErreur(null);
    setReponse(null);
    try {
      const r = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!r.ok) throw new ErreurApi(r.status === 422 ? "Question refusée par l'API (3 à 1000 caractères)." : `Erreur ${r.status} de l'API locale : le service de génération est peut-être arrêté (Ollama).`);
      setReponse((await r.json()) as Reponse);
    } catch (err) {
      setErreur(err instanceof ErreurApi ? err.message : "L'API locale ne répond pas. Lancez le backend (voir le README), puis réessayez.");
    } finally {
      setEnCours(false);
    }
  }

  const repondu = reponse?.decision === "repondre";
  const tout = reponse
    ? `Question : ${question.trim()}\n\n${reponse.reponse}\n\n` +
      reponse.citations.map((c, i) => `[${i + 1}] ${texteCitation(c)}`).join("\n\n") +
      `\n\n${reponse.avertissement}`
    : "";

  return (
    <>
      <header className="entete">
        <div className="colonne">
          <p className="marque">Veille MiCA</p>
          <h1>Veille réglementaire sur les crypto-actifs</h1>
          <p className="intro">
            Posez une question en français. La réponse cite le passage exact du texte officiel, avec sa source. Si les textes du
            corpus ne permettent pas de répondre, l'outil le dit et ne répond pas.
          </p>
        </div>
      </header>

      <main className="colonne">
        <section aria-labelledby="t-question" className="bloc-question">
          <form onSubmit={poser}>
            <label id="t-question" htmlFor="question">Votre question</label>
            <textarea
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={4}
              maxLength={1000}
              placeholder="Par exemple : À partir de quelle date MiCA est-il applicable ?"
            />
            <div className="ligne">
              <span className="aide-champ">{question.length} / 1000 caractères</span>
              <button type="submit" className="principal" disabled={enCours}>
                {enCours ? "Recherche en cours…" : "Poser la question"}
              </button>
            </div>
          </form>

          <div className="exemples">
            <p className="etiquette">Exemples de questions</p>
            <ul>
              {EXEMPLES.map((ex) => (
                <li key={ex}>
                  <button type="button" className="lien-bouton" disabled={enCours} onClick={() => { setQuestion(ex); void poser(undefined, ex); }}>
                    {ex}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {erreur && <p className="erreur" role="alert">{erreur}</p>}

        {enCours && <p className="attente" role="status">Recherche dans les textes et vérification des citations. La première réponse peut prendre une minute.</p>}

        {reponse && (
          <section className="resultat" aria-live="polite" aria-labelledby="t-reponse">
            <h2 id="t-reponse" className="etiquette">{repondu ? "Réponse" : "Pas de réponse"}</h2>
            <p className="question-imprimee">Question : {question.trim()}</p>
            <p className={repondu ? "statut" : "statut refus"}>
              {repondu ? "Réponse fondée sur les passages cités ci-dessous" : `Refus : ${LIBELLES_MOTIF[reponse.motif ?? ""] ?? reponse.motif}`}
            </p>
            <p className="reponse">{reponse.reponse}</p>
            {reponse.decision === "refuser" && (reponse.motif === "hors_corpus" || reponse.motif === "passages_insuffisants") && (
              <p className="aide">
                Si votre question porte bien sur les textes du corpus, essayez de la reformuler avec les termes du texte (par exemple
                « période transitoire », « article 143 », « date d'application »). Une même question formulée autrement peut être refusée à tort.
              </p>
            )}

            {reponse.citations.length > 0 && (
              <>
                <h3 className="etiquette sources">Sources citées ({reponse.citations.length})</h3>
                <ol className="citations">
                  {reponse.citations.map((c) => (
                    <li key={c.chunk_id}>
                      <details>
                        <summary>
                          <span className="ref">{c.reference}</span>
                          <span className="src">{c.source_titre}</span>
                          {c.contraignant !== "oui" && <span className="tag">{c.contraignant === "non" ? "non contraignant" : "statut non vérifié"}</span>}
                        </summary>
                        <blockquote>{c.texte}</blockquote>
                        <p className="meta">
                          {c.identifiant} · version : {c.version} · consulté le {c.date_consultation}
                        </p>
                        <p className="outils">
                          <BoutonCopier texte={texteCitation(c)} libelle="Copier la citation" />
                          <a href={c.url} target="_blank" rel="noopener noreferrer">Source officielle<span className="sr"> (nouvel onglet)</span></a>
                        </p>
                      </details>
                    </li>
                  ))}
                </ol>
              </>
            )}

            <p className="outils barre-outils">
              <BoutonCopier texte={tout} libelle="Copier la réponse avec ses sources" />
              <button type="button" className="lien-bouton" onClick={() => window.print()}>Imprimer</button>
            </p>
            <p className="pied-reponse">{reponse.avertissement}</p>
          </section>
        )}

        <section className="info" aria-labelledby="t-methode">
          <h2 id="t-methode">Méthode</h2>
          <ol className="methode">
            <li><strong>Recherche.</strong> Les textes sont découpés par article, paragraphe et définition, puis indexés pour retrouver les passages les plus proches de la question.</li>
            <li><strong>Réponse limitée aux passages.</strong> Le modèle choisit uniquement parmi les passages retrouvés. Le texte cité vient de la base et n'est jamais réécrit.</li>
            <li><strong>Contrôles et refus.</strong> Hors corpus, passages insuffisants, demande d'avis sur un cas particulier, nombre absent des sources : l'outil refuse.</li>
          </ol>
        </section>

        <section className="info" aria-labelledby="t-corpus">
          <h2 id="t-corpus">Textes du corpus</h2>
          <ul className="corpus">
            {CORPUS.map((c) => <li key={c}>{c}</li>)}
          </ul>
          <p className="note">Les textes non contraignants sont signalés comme tels dans les citations. La méthode d'évaluation et les limites sont décrites dans le dépôt (dossiers docs et eval).</p>
        </section>
      </main>

      <footer className="pied">
        <div className="colonne">
          <p><strong>Ceci n'est pas un conseil juridique.</strong></p>
          <p>Projet indépendant, non affilié à une autorité publique. Démonstration technique fonctionnant en local, sans cookie ni traceur.</p>
        </div>
      </footer>
    </>
  );
}
