"""Contrôles faits par le système, indépendants du modèle.

Contrôle des nombres : chaque suite de chiffres de la réponse doit figurer dans les passages cités
ou dans leurs métadonnées. C'est une heuristique : elle attrape une date ou un montant inventé
(ou tiré de la mémoire du modèle), pas une phrase fausse qui n'utilise que des nombres présents.
"""
import re

RE_MILLIERS = re.compile(r"(?<=\d)[   ](?=\d{3}(?!\d))")
RE_NOMBRE = re.compile(r"\d+")


def nombres(texte: str) -> set[str]:
    """Suites de chiffres d'un texte, séparateurs de milliers retirés (« 1 000 » devient 1000)."""
    return set(RE_NOMBRE.findall(RE_MILLIERS.sub("", texte)))


def texte_verifiable(passage: dict) -> str:
    """Texte du passage plus ses métadonnées : le numéro d'article ou de point vit dans les métadonnées."""
    meta = [str(passage.get(c, "")) for c in ("article", "paragraphe", "point", "identifiant", "source_titre", "titre", "chunk_id")]
    return passage["texte"] + "\n" + "\n".join(meta)


def controle_nombres(reponse: str, passages_cites: list[dict], question: str = "") -> dict:
    """Les nombres de la question sont autorisés : un refus peut la reformuler (« le règlement 2024/1624 n'est pas dans
    les textes ») sans que ce soit un nombre inventé. Une date absente de la question et des passages reste rejetée."""
    autorises: set[str] = nombres(question)
    for p in passages_cites:
        autorises |= nombres(texte_verifiable(p))
    inconnus = sorted(nombres(reponse) - autorises, key=lambda x: (len(x), x))
    return {"ok": not inconnus, "inconnus": inconnus}
