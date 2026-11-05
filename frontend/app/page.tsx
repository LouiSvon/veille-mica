"use client";

import { FormEvent, useState } from "react";
import { API_URL, LIBELLES_MOTIF, type Reponse } from "../lib/types";

const EXEMPLES = [
  "Jusqu'à quand les prestataires qui fournissaient déjà leurs services avant le 30 décembre 2024 peuvent-ils continuer sans agrément MiCA ?",
  "Comment MiCA définit-il un crypto-actif ?",
  "À partir de quelle date les orientations de l'ABE sur la travel rule s'appliquent-elles ?",
];

class ErreurApi extends Error {}

export default function Page() {
  const [question, setQuestion] = useState("");
  const [reponse, setReponse] = useState<Reponse | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

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

  return (
    <>
      <header className="entete">
        <div className="conteneur">
          <div className="barre">
            <div className="marque">
              <span className="logo" aria-hidden="true">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M3 2h7l3 3v9H3z" /><path d="M5.5 8h5M5.5 11h5" /></svg>
              </span>
              Veille MiCA
            </div>
            <span className="pastille">100 % local, aucune donnée envoyée à un service tiers</span>
          </div>
        </div>
        <div className="hero">
         <div className="conteneur">
            <h1>La réglementation des crypto-actifs, citée au mot près.</h1>
            <p>
              Posez une question en français. L'assistant retrouve le passage exact dans les textes officiels, le cite avec sa source,
              et refuse de répondre quand le corpus ne permet pas de le faire.
            </p>
            <ul className="preuves">
              <li>Citation du passage exact</li>
              <li>Refus explicite hors corpus</li>
              <li>Évaluation mesurée et publiée</li>
            </ul>
         </div>
        </div>
      </header>

      <main className="conteneur">
        <form className="panneau recherche" onSubmit={poser}>
          <label htmlFor="question">Votre question</label>
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
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

        <h2 className="titre-section">Questions d'exemple</h2>
        <div className="exemples" aria-label="Exemples de questions">
          {EXEMPLES.map((ex) => (
            <button key={ex} type="button" className="exemple" disabled={enCours} onClick={() => { setQuestion(ex); void poser(undefined, ex); }}>
              {ex}
            </button>
          ))}
        </div>

        {erreur && <p className="erreur" role="alert">{erreur}</p>}

        {enCours && (
          <section className="panneau resultat attente" role="status">
            <span className="rond" aria-hidden="true" />
            Recherche dans les textes et vérification des citations. Une première réponse peut prendre une minute.
          </section>
        )}

        {reponse && (
          <section className="panneau resultat" aria-live="polite">
            <p className={reponse.decision === "repondre" ? "badge ok" : "badge refus"}>
              {reponse.decision === "repondre" ? "Réponse sourcée" : `Refus : ${LIBELLES_MOTIF[reponse.motif ?? ""] ?? reponse.motif}`}
            </p>
            <p className="texte">{reponse.reponse}</p>
            {reponse.decision === "refuser" && (reponse.motif === "hors_corpus" || reponse.motif === "passages_insuffisants") && (
              <p className="aide">
                Si votre question porte bien sur les textes du corpus, essayez de la reformuler avec les termes du texte (par exemple
                « période transitoire », « article 143 », « date d'application »). Une même question formulée autrement peut être refusée à tort.
              </p>
            )}

            {reponse.citations.length > 0 && (
              <>
                <h2 className="sous">Passages cités</h2>
                <ul className="citations">
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
                          {c.identifiant} · version : {c.version} · consulté le {c.date_consultation} ·{" "}
                          <a href={c.url} target="_blank" rel="noopener noreferrer">source officielle</a>
                        </p>
                      </details>
                    </li>
                  ))}
                </ul>
              </>
            )}
            <p className="pied">{reponse.avertissement}</p>
          </section>
        )}

        <h2 className="titre-section">Comment ça marche</h2>
        <div className="etapes">
          <div className="etape">
            <div className="num">1</div>
            <h3>Recherche dans les textes</h3>
            <p>Les textes sont découpés par article, paragraphe et définition, puis indexés pour retrouver les passages les plus proches de la question.</p>
          </div>
          <div className="etape">
            <div className="num">2</div>
            <h3>Réponse limitée aux passages</h3>
            <p>Le modèle ne choisit que parmi les passages retrouvés. Le texte cité vient de la base, il n'est jamais réécrit.</p>
          </div>
          <div className="etape">
            <div className="num">3</div>
            <h3>Contrôles et refus</h3>
            <p>Hors corpus, passages insuffisants, demande d'avis sur un cas particulier ou nombre non retrouvé dans les sources : l'outil refuse.</p>
          </div>
        </div>

        <h2 className="titre-section">Corpus</h2>
        <ul className="corpus" aria-label="Textes du corpus">
          <li>Règlement MiCA (UE) 2023/1114</li>
          <li>Règlement sur les transferts de fonds (UE) 2023/1113</li>
          <li>Orientations de l'ABE</li>
          <li>Position de l'AMF</li>
          <li>Ordonnance n° 2024-936</li>
        </ul>
        <p className="note">Les textes non contraignants sont signalés comme tels dans les citations. Les limites et la méthode d'évaluation sont décrites dans le dépôt (dossiers docs et eval).</p>
      </main>

      <footer>
        <div className="conteneur">Ceci n'est pas un conseil juridique. Outil de démonstration fonctionnant en local.</div>
      </footer>
    </>
  );
}
