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
    <main>
      <h1>Veille réglementaire sur les crypto-actifs</h1>
      <p className="soustitre">
        Posez une question en français. La réponse cite le passage exact du texte officiel, ou refuse si les textes du corpus ne
        permettent pas de répondre.
      </p>

      <form onSubmit={poser}>
        <label htmlFor="question">Votre question</label>
        <textarea
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          maxLength={1000}
          placeholder="Par exemple : À partir de quelle date MiCA est-il applicable ?"
        />
        <div className="actions">
          <button type="submit" disabled={enCours}>
            {enCours ? "Recherche en cours…" : "Poser la question"}
          </button>
        </div>
      </form>

      <div className="exemples" aria-label="Exemples de questions">
        {EXEMPLES.map((ex) => (
          <button key={ex} type="button" className="puce" disabled={enCours} onClick={() => { setQuestion(ex); void poser(undefined, ex); }}>
            {ex}
          </button>
        ))}
      </div>

      {erreur && <p className="erreur" role="alert">{erreur}</p>}

      {reponse && (
        <section className="carte" aria-live="polite">
          <p className={reponse.decision === "repondre" ? "badge ok" : "badge refus"}>
            {reponse.decision === "repondre" ? "Réponse" : `Refus : ${LIBELLES_MOTIF[reponse.motif ?? ""] ?? reponse.motif}`}
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
              <h2>Passages cités</h2>
              <ul className="citations">
                {reponse.citations.map((c) => (
                  <li key={c.chunk_id}>
                    <details>
                      <summary>
                        <span className="ref">{c.reference}</span> : {c.source_titre}
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
    </main>
  );
}
