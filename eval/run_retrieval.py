"""Mesure la recherche (BM25, vecteurs, hybride) sur les questions validées : recall@k, MRR, intervalle de Wilson.

Usage :
    backend/.venv/bin/python eval/run_retrieval.py                 # questions de développement (réglage)
    backend/.venv/bin/python eval/run_retrieval.py --split test    # test figé : à ne lancer qu'une fois la configuration arrêtée

Seules les questions "répondables" et validées par Louis comptent. Le rapport est daté et écrit dans eval/reports/.
Le test figé n'est pas utilisé pour régler le système : le script demande une confirmation explicite.
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))

from app.evaluation.metrics import mrr, premier_rang, recall_at_k, wilson  # noqa: E402
from app.retrieval.dense import embedder_ollama  # noqa: E402
from app.retrieval.retriever import Retriever  # noqa: E402

MODES = ("bm25", "dense", "hybride")
VALIDES = {"valide", "corrige", "delegue"}  # "delegue" : choisie par l'assistant sur délégation de Louis, signalé dans le rapport


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=("dev", "test"), default="dev")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--confirmer-test", action="store_true", help="requis pour lire le test figé")
    a = p.parse_args()
    if a.split == "test" and not a.confirmer_test:
        print("Le test est figé : relance avec --confirmer-test seulement quand la configuration est arrêtée.", file=sys.stderr)
        return 2

    chunks = RACINE / "data" / "processed" / "chunks.jsonl"
    questions = [json.loads(l) for l in (RACINE / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    retenues = [q for q in questions if q["split"] == a.split and q["statut"] == "repondable" and q["validation"] in VALIDES]
    if not retenues:
        print("Aucune question répondable validée pour ce split.", file=sys.stderr)
        return 1

    retriever = Retriever.depuis_fichier(chunks, embedder=embedder_ollama(), cache=RACINE / "data" / "processed" / "embeddings.npz", nom_modele="bge-m3")
    rapport = {
        "date": str(date.today()), "split": a.split, "k": a.k, "n_questions": len(retenues),
        "modele_embedding": "bge-m3", "rrf_k": 60, "candidats": 50,
        "empreinte_corpus": hashlib.sha256(chunks.read_bytes()).hexdigest(),
        "validations": {v: sum(q["validation"] == v for q in retenues) for v in sorted({q["validation"] for q in retenues})},
        "modes": {},
    }
    for mode in MODES:
        rangs, details = [], []
        for q in retenues:
            refs = {r["chunk_id"] for r in q["passages_reference"]}
            classement = [x["passage"]["chunk_id"] for x in retriever.chercher(q["question"], k=10, mode=mode)]
            rang = premier_rang(classement, refs)
            rangs.append(rang)
            details.append({"id": q["id"], "rang": rang})
        k_ok, n = recall_at_k(rangs, a.k)
        bas, haut = wilson(k_ok, n)
        rapport["modes"][mode] = {
            f"recall_at_{a.k}": {"k": k_ok, "n": n, "wilson_95": [round(bas, 3), round(haut, 3)]},
            "mrr_at_10": round(mrr(rangs), 3), "details": details,
        }
        print(f"{mode:8} recall@{a.k} {k_ok}/{n} (Wilson 95 % : {bas:.2f} à {haut:.2f})  MRR@10 {mrr(rangs):.2f}  rangs : "
              + " ".join(f"{d['id']}:{d['rang'] or '-'}" for d in details))
    sortie = RACINE / "eval" / "reports" / f"retrieval-{rapport['date']}-{a.split}.json"
    sortie.write_text(json.dumps(rapport, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"rapport : {sortie.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
