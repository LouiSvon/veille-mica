"""Recherche vectorielle : embeddings via Ollama (bge-m3), similarité cosinus avec numpy.

Les vecteurs sont normalisés : le cosinus devient un produit scalaire. Un cache sur disque évite de
recalculer les embeddings d'un passage dont le texte n'a pas changé (clé : empreinte du texte indexé).
"""
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Callable

import numpy as np

MODELE_PAR_DEFAUT = "bge-m3"
URL_OLLAMA = "http://localhost:11434"
TAILLE_LOT = 16

Embedder = Callable[[list[str]], np.ndarray]


def embedder_ollama(modele: str = MODELE_PAR_DEFAUT, url: str = URL_OLLAMA) -> Embedder:
    def embed(textes: list[str]) -> np.ndarray:
        morceaux = []
        for i in range(0, len(textes), TAILLE_LOT):
            requete = urllib.request.Request(
                f"{url}/api/embed",
                data=json.dumps({"model": modele, "input": textes[i:i + TAILLE_LOT]}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(requete, timeout=300) as r:
                morceaux.append(np.array(json.load(r)["embeddings"], dtype=np.float32))
        return normaliser(np.vstack(morceaux)) if morceaux else np.zeros((0, 0), dtype=np.float32)

    return embed


def normaliser(m: np.ndarray) -> np.ndarray:
    normes = np.linalg.norm(m, axis=1, keepdims=True)
    normes[normes == 0] = 1.0
    return m / normes


def empreinte(texte: str) -> str:
    return hashlib.sha256(texte.encode("utf-8")).hexdigest()


class IndexDense:
    def __init__(self, vecteurs: np.ndarray):
        self.vecteurs = vecteurs

    def classer(self, vecteur_requete: np.ndarray, k: int) -> list[tuple[int, float]]:
        q = normaliser(vecteur_requete.reshape(1, -1))[0]
        scores = self.vecteurs @ q
        ordre = np.lexsort((np.arange(len(scores)), -scores))[:k]
        return [(int(i), float(scores[i])) for i in ordre]


def construire_index(textes: list[str], embedder: Embedder, cache: Path | None = None, nom_modele: str = "") -> IndexDense:
    """Embeddings de tous les textes ; seuls les textes absents du cache sont calculés."""
    cles = [empreinte(nom_modele + "\n" + t) for t in textes]
    connus: dict[str, np.ndarray] = {}
    if cache is not None and cache.exists():
        with np.load(cache, allow_pickle=False) as f:
            connus = dict(zip(f["cles"].tolist(), f["vecteurs"]))
    manquants = [i for i, c in enumerate(cles) if c not in connus]
    if manquants:
        nouveaux = embedder([textes[i] for i in manquants])
        for i, v in zip(manquants, nouveaux):
            connus[cles[i]] = v
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            vus = list(connus)
            np.savez(cache, cles=np.array(vus), vecteurs=np.vstack([connus[c] for c in vus]))
    return IndexDense(np.vstack([connus[c] for c in cles]) if cles else np.zeros((0, 0), dtype=np.float32))
