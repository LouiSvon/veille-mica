"""Sonde exploratoire : le passage de référence reste-t-il retrouvé quand la question est reformulée ?

Ce n'est pas un score du jeu validé : les paraphrases sont écrites par l'assistant, la taille est petite (n = 10),
et la sonde ne sert qu'à documenter une sensibilité à la formulation observée dans l'interface.
Retrieval seul (pas de génération). Écrit eval/reports/robustesse-paraphrases-<date>.json.
"""
import json
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))
from app.evaluation.metrics import premier_rang  # noqa: E402
from app.retrieval.dense import embedder_ollama  # noqa: E402
from app.retrieval.retriever import Retriever  # noqa: E402

SONDE = {
    "q008": ("mica-art-143", [
        "Jusqu'à quand les prestataires déjà actifs peuvent-ils continuer sans agrément MiCA ?",
        "Jusqu'à quelle date la période transitoire permet-elle de continuer sans agrément ?",
        "Les prestataires existants ont-ils un délai avant d'obtenir un agrément MiCA ?"]),
    "q007": ("mica-art-149", [
        "Quand MiCA s'applique-t-il ?", "Date d'entrée en application du règlement MiCA", "MiCA est applicable depuis quand ?"]),
    "q010": ("eba-gl-2024-11-par-10", [
        "Quand les orientations de l'ABE sur les règles de voyage sont-elles applicables ?", "Date d'application des orientations EBA/GL/2024/11"]),
    "q004": ("mica-art-3-p1-pt5", ["Qu'est-ce qu'un crypto-actif dans MiCA ?", "Définition de crypto-actif selon le règlement MiCA"]),
}


def main() -> int:
    r = Retriever.depuis_fichier(RACINE / "data/processed/chunks.jsonl", embedder=embedder_ollama(),
                                 cache=RACINE / "data/processed/embeddings.npz", nom_modele="bge-m3")
    lignes, tot = [], {m: [0, 0] for m in ("bm25", "dense", "hybride")}
    for qid, (ref, variantes) in SONDE.items():
        for v in variantes:
            rangs = {}
            for mode in tot:
                res = r.chercher(v, k=10, mode=mode)
                rg = premier_rang([x["passage"]["chunk_id"] for x in res], {ref})
                rangs[mode] = rg
                tot[mode][1] += 1
                tot[mode][0] += int(rg is not None and rg <= 5)
            lignes.append({"question_source": qid, "paraphrase": v, "reference": ref, "rangs": rangs})
            print(f"{qid} bm25={rangs['bm25'] or '-'!s:>2} dense={rangs['dense'] or '-'!s:>2} hybride={rangs['hybride'] or '-'!s:>2}  {v}")
    resume = {m: f"{a}/{b}" for m, (a, b) in tot.items()}
    print("\nrecall@5 sur les paraphrases :", resume)
    sortie = RACINE / "eval/reports" / f"robustesse-paraphrases-{date.today()}.json"
    sortie.write_text(json.dumps({"date": str(date.today()), "n": len(lignes), "recall_at_5": resume,
                                  "avertissement": "exploratoire, paraphrases écrites par l'assistant", "detail": lignes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("rapport :", sortie.relative_to(RACINE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
