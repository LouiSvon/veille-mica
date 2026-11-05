"""Mesure l'assistant complet (recherche, refus en deux couches, génération, vérifications) sur les questions validées.

Usage :
    backend/.venv/bin/python eval/run_generation.py --modele qwen3.5:9b                  # questions de développement
    backend/.venv/bin/python eval/run_generation.py --modele X --split test --confirmer-test

Les règles de réussite sont celles de docs/regles-notation.md, écrites avant la première exécution :
- repondable : décision « repondre », une citation parmi les passages de référence, contrôle des nombres réussi ;
- hors_corpus et piège sur texte inexistant : refus de motif hors_corpus ou passages_insuffisants ;
- piège d'avis juridique (q023, q024 en test ; q042, q043 en développement) : refus de motif avis_juridique.
Les refus techniques (echec_*) ne comptent jamais comme refus justifié. La justesse du contenu n'est PAS notée ici :
le rapport contient toutes les réponses pour relecture. Toute note de justesse produite par l'assistant est étiquetée
« notation de l'assistant, non vérifiée par Louis ».
"""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))

from app.evaluation.metrics import wilson  # noqa: E402
from app.generation.llm import OllamaLLM  # noqa: E402
from app.generation.pipeline import Config, repondre  # noqa: E402
from app.retrieval.dense import embedder_ollama  # noqa: E402
from app.retrieval.retriever import Retriever  # noqa: E402

VALIDES = {"valide", "corrige", "delegue"}
AVIS_JURIDIQUE = {"q023", "q024", "q042", "q043"}  # pièges d'avis sur un cas particulier (voir leur comportement_attendu)
REFUS_JUSTIFIES = {"hors_corpus", "passages_insuffisants"}


def reussite(q: dict, r) -> tuple[bool, str]:
    """Applique la règle du statut. Retourne (réussite, raison courte)."""
    if q["statut"] == "repondable":
        refs = {x["chunk_id"] for x in q["passages_reference"]}
        if r.decision != "repondre":
            return False, f"faux refus ({r.motif}, couche {r.couche_refus})"
        if not any(c.chunk_id in refs for c in r.citations):
            return False, "aucune citation de référence"
        if not r.controle_nombres.get("ok", False):
            return False, "contrôle des nombres échoué"
        return True, "répondu et sourcé"
    if q["id"] in AVIS_JURIDIQUE:
        ok = r.decision == "refuser" and r.motif == "avis_juridique"
        return ok, "refus avis_juridique" if ok else f"attendu avis_juridique, obtenu {r.decision}/{r.motif}"
    ok = r.decision == "refuser" and r.motif in REFUS_JUSTIFIES
    return ok, "refus justifié" if ok else f"attendu un refus justifié, obtenu {r.decision}/{r.motif}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--modele", required=True)
    p.add_argument("--split", choices=("dev", "test"), default="dev")
    p.add_argument("--confirmer-test", action="store_true")
    p.add_argument("--mode", default=Config.mode, choices=("bm25", "dense", "hybride"))
    p.add_argument("--seuil", type=float, default=Config.seuil_cosinus)
    a = p.parse_args()
    if a.split == "test" and not a.confirmer_test:
        print("Le test est figé : relance avec --confirmer-test seulement quand la configuration est arrêtée.", file=sys.stderr)
        return 2

    questions = [json.loads(l) for l in (RACINE / "eval/questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    retenues = [q for q in questions if q["split"] == a.split and q["validation"] in VALIDES]
    retriever = Retriever.depuis_fichier(RACINE / "data/processed/chunks.jsonl", embedder=embedder_ollama(),
                                         cache=RACINE / "data/processed/embeddings.npz", nom_modele="bge-m3")
    llm = OllamaLLM(a.modele)
    cfg = Config(mode=a.mode, seuil_cosinus=a.seuil)
    detail, par_statut = [], {}
    for q in retenues:
        t0 = time.time()
        r = repondre(q["question"], retriever, llm, cfg)
        duree = round(time.time() - t0, 1)
        ok, raison = reussite(q, r)
        statut = "avis_juridique" if q["id"] in AVIS_JURIDIQUE else q["statut"]
        par_statut.setdefault(statut, []).append(ok)
        detail.append({
            "id": q["id"], "statut": statut, "question": q["question"], "reussite": ok, "raison": raison,
            "decision": r.decision, "motif": r.motif, "couche_refus": r.couche_refus, "reponse": r.reponse,
            "citations": [c.chunk_id for c in r.citations], "controle_nombres": r.controle_nombres,
            "attendu": q["reponse_attendue"] or q["comportement_attendu"], "validation_question": q["validation"],
            "duree_s": duree, "diagnostic": r.diagnostic,
        })
        print(f"{q['id']} {statut:14} {'OK ' if ok else 'ECHEC'} {raison:55} {duree:5.1f}s")

    resume = {}
    for statut, oks in par_statut.items():
        bas, haut = wilson(sum(oks), len(oks))
        resume[statut] = {"reussites": sum(oks), "n": len(oks), "wilson_95": [round(bas, 3), round(haut, 3)]}
    couches: dict[str, int] = {}
    for d in detail:
        if d["decision"] == "refuser":
            cle = f"{d['couche_refus']}/{d['motif']}"
            couches[cle] = couches.get(cle, 0) + 1
    rapport = {
        "date": str(date.today()), "split": a.split, "modele": a.modele, "mode_recherche": a.mode,
        "seuil_cosinus": a.seuil, "num_ctx": llm.num_ctx, "seed": llm.seed, "think": False,
        "n_questions": len(detail), "resume_par_statut": resume, "refus_par_couche_et_motif": couches,
        "note": "Justesse du contenu non notée ici. Toute note de justesse de l'assistant est non vérifiée par Louis.",
        "detail": detail,
    }
    nom = a.modele.replace(":", "-").replace("/", "-")
    sortie = RACINE / "eval/reports" / f"generation-{rapport['date']}-{a.split}-{nom}-{a.mode}.json"
    sortie.write_text(json.dumps(rapport, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nRésumé :")
    for statut, v in resume.items():
        print(f"  {statut:14} {v['reussites']}/{v['n']}  Wilson 95 % {v['wilson_95'][0]:.2f} à {v['wilson_95'][1]:.2f}")
    print("Refus par couche/motif :", couches)
    print("rapport :", sortie.relative_to(RACINE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
