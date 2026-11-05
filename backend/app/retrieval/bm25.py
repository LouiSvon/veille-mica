"""BM25 (Okapi) écrit à la main, avec une normalisation adaptée au français juridique.

Pourquoi à la main : le corpus tient en quelques centaines de passages, et on veut contrôler la
tokenisation (accents, numéros d'articles, références comme 2023/1113) et pouvoir expliquer chaque ligne.
"""
import math
import re
import unicodedata
from collections import Counter

STOP = frozenset(
    "le la les l un une des de du d et en au aux a ce ces cette son sa ses leur leurs que qui quoi dont ou "
    "par pour sur dans avec sans sous est sont etre ete il elle ils elles on se s y n ne pas plus ni si "
    "comme mais donc or car nous vous je tu lui eux qu c j m t".split()
)
RE_REFERENCE = re.compile(r"\d+/\d+")  # 2023/1113, 2015/849
RE_MOT = re.compile(r"[a-z0-9]+")


def sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def racine_legere(mot: str) -> str:
    """Retire un pluriel simple. Volontairement minimal : un vrai racinisateur cacherait des erreurs."""
    if len(mot) > 4 and mot.endswith(("s", "x")):
        return mot[:-1]
    return mot


def tokeniser(texte: str) -> list[str]:
    t = sans_accents(texte.lower().replace("’", "'"))
    jetons = RE_REFERENCE.findall(t)  # on garde la référence entière, en plus de ses chiffres
    for mot in RE_MOT.findall(t):
        if mot in STOP or (len(mot) == 1 and not mot.isdigit()):
            continue
        jetons.append(racine_legere(mot))
    return jetons


class BM25:
    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokeniser(d)) for d in documents]
        self.longueurs = [sum(tf.values()) for tf in self.tfs]
        self.n = len(documents)
        self.moyenne = (sum(self.longueurs) / self.n) if self.n else 0.0
        df: Counter = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        self.idf = {t: math.log(1 + (self.n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self.index: dict[str, list[int]] = {}
        for i, tf in enumerate(self.tfs):
            for t in tf:
                self.index.setdefault(t, []).append(i)

    def scores(self, requete: str) -> dict[int, float]:
        resultat: dict[int, float] = {}
        for t in set(tokeniser(requete)):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i in self.index[t]:
                f = self.tfs[i][t]
                denom = f + self.k1 * (1 - self.b + self.b * self.longueurs[i] / self.moyenne)
                resultat[i] = resultat.get(i, 0.0) + idf * f * (self.k1 + 1) / denom
        return resultat

    def classer(self, requete: str, k: int) -> list[tuple[int, float]]:
        s = self.scores(requete)
        return sorted(s.items(), key=lambda x: (-x[1], x[0]))[:k]
