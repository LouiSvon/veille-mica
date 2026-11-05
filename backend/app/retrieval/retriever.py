"""Recherche hybride : BM25 + vecteurs, fusionnés par Reciprocal Rank Fusion (RRF).

RRF ne compare pas les scores (BM25 et cosinus n'ont pas la même échelle) : il additionne 1 / (k + rang)
sur chaque liste. Un passage bien classé par les deux méthodes passe devant un passage classé premier par une seule.
"""
import json
from pathlib import Path
from typing import Literal

from app.retrieval.bm25 import BM25
from app.retrieval.dense import Embedder, IndexDense, construire_index

Mode = Literal["bm25", "dense", "hybride"]
RRF_K = 60  # valeur usuelle de la littérature ; réglable sur les questions de développement
CANDIDATS = 50  # profondeur de chaque liste avant fusion


def texte_indexe(p: dict) -> str:
    """Texte vu par BM25 et par les embeddings : l'intitulé de la source et du passage précède le texte,
    pour que « article 143 » ou « règlement 2023/1113 » dans une question retrouve le bon passage."""
    if p["type"] == "article":
        etiquette = f"article {p['article']}" + (f" paragraphe {p['paragraphe']}" if p["paragraphe"] else "")
        if p.get("point"):
            etiquette += f" point {p['point']} définition"
    else:
        etiquette = p["article"]
    return f"{p['source_titre']} | {etiquette} | {p['titre']}\n{p['texte']}"


def fusion_rrf(listes: list[list[int]], k: int = RRF_K) -> list[tuple[int, float]]:
    score: dict[int, float] = {}
    for liste in listes:
        for rang, i in enumerate(liste, start=1):
            score[i] = score.get(i, 0.0) + 1.0 / (k + rang)
    return sorted(score.items(), key=lambda x: (-x[1], x[0]))


class Retriever:
    def __init__(self, passages: list[dict], embedder: Embedder | None = None, cache: Path | None = None, nom_modele: str = ""):
        self.passages = passages
        textes = [texte_indexe(p) for p in passages]
        self.bm25 = BM25(textes)
        self.embedder = embedder
        self.dense: IndexDense | None = construire_index(textes, embedder, cache, nom_modele) if embedder else None

    @classmethod
    def depuis_fichier(cls, chemin: Path, **kw) -> "Retriever":
        passages = [json.loads(l) for l in chemin.read_text(encoding="utf-8").splitlines() if l.strip()]
        return cls(passages, **kw)

    def chercher(self, question: str, k: int = 5, mode: Mode = "hybride") -> list[dict]:
        """Retourne les k meilleurs passages : {"passage", "rang", "score", "mode"}."""
        if mode == "bm25":
            classement = self.bm25.classer(question, k)
        elif mode == "dense":
            classement = self._dense(question, k)
        else:
            liste_b = [i for i, _ in self.bm25.classer(question, CANDIDATS)]
            liste_d = [i for i, _ in self._dense(question, CANDIDATS)]
            classement = fusion_rrf([liste_b, liste_d])[:k]
        return [
            {"passage": self.passages[i], "rang": r, "score": s, "mode": mode}
            for r, (i, s) in enumerate(classement, start=1)
        ]

    def _dense(self, question: str, k: int) -> list[tuple[int, float]]:
        if self.dense is None or self.embedder is None:
            raise RuntimeError("recherche vectorielle indisponible : aucun embedder fourni")
        return self.dense.classer(self.embedder([question])[0], k)
