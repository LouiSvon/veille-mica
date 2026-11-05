"""Dérive le seuil de la couche 1 par la règle de docs/regles-notation.md, sans choisir la valeur à la main.

Règle : seuil = (plus petit cosinus du meilleur passage parmi les questions répondables du dev) - 0,03, arrondi vers le bas à 2 décimales.
Ne lit jamais le test figé.
"""
import json
import math
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))
from app.retrieval.dense import embedder_ollama  # noqa: E402
from app.retrieval.retriever import Retriever  # noqa: E402

VALIDES = {"valide", "corrige", "delegue"}
MARGE = 0.03


def main() -> int:
    r = Retriever.depuis_fichier(RACINE / "data/processed/chunks.jsonl", embedder=embedder_ollama(),
                                 cache=RACINE / "data/processed/embeddings.npz", nom_modele="bge-m3")
    qs = [json.loads(l) for l in (RACINE / "eval/questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    dev = [q for q in qs if q["split"] == "dev" and q["validation"] in VALIDES]
    lignes = []
    for q in dev:
        _, sig = r.rechercher(q["question"], k=1, mode="dense")
        lignes.append((q["id"], q["statut"], sig["cosinus_top1"]))
    repondables = [c for _, st, c in lignes if st == "repondable"]
    seuil = math.floor((min(repondables) - MARGE) * 100) / 100
    for i, st, c in sorted(lignes, key=lambda x: x[2]):
        print(f"{i} {st:12} cos1={c:.3f}  {'écartée par la couche 1' if c < seuil else 'passe la couche 1'}")
    print(f"\nplus petit cosinus répondable : {min(repondables):.3f} ; marge {MARGE} ; seuil dérivé : {seuil:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
