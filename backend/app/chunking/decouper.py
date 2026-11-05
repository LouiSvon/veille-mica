"""Découpe un texte EUR-Lex (XHTML) en passages citables : un article, ou un paragraphe si l'article est long.

Chaque passage garde le texte mot pour mot, car l'assistant doit citer le texte officiel.
"""
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

# Au-delà de ce nombre de caractères, un article est découpé par paragraphe numéroté.
SEUIL_CARACTERES = 3500

ID_ARTICLE = re.compile(r"^art_(\d+)$")
ID_ANNEXE = re.compile(r"^anx_([IVX]+)$")
ID_PARAGRAPHE = re.compile(r"^\d{3}\.\d{3}$")


def normaliser(texte: str) -> str:
    return re.sub(r"\s+", " ", texte.replace("\xa0", " ")).strip()


def texte_de(noeud) -> str:
    """Texte d'un noeud. Un item de liste (a), b)...) tient dans deux cellules : on les rejoint sur une ligne."""
    lignes = []
    for fils in noeud.find_all(["p", "table"], recursive=False):
        if fils.name == "table":
            for tr in fils.find_all("tr"):
                lignes.append(normaliser(" ".join(td.get_text(" ") for td in tr.find_all("td"))))
        else:
            lignes.append(normaliser(fils.get_text(" ")))
    return "\n".join(ligne for ligne in lignes if ligne)


def segmenter_ligne(ligne: str, seuil: int = SEUIL_CARACTERES) -> list[str]:
    """Coupe une ligne géante aux fins de phrase ou de proposition (; . :). Le texte reste mot pour mot ;
    une phrase seule plus longue que le seuil reste entière."""
    if len(ligne) <= seuil:
        return [ligne]
    morceaux, courant = [], ""
    for partie in re.split(r"(?<=[;.:])\s+", ligne):
        if courant and len(courant) + 1 + len(partie) > seuil:
            morceaux.append(courant)
            courant = partie
        else:
            courant = (courant + " " + partie).strip()
    if courant:
        morceaux.append(courant)
    return morceaux


def sous_decouper(texte: str) -> list[str]:
    """Coupe un texte géant (définitions, annexes) par lignes entières, en répétant la première ligne comme introduction.

    La ligne répétée est du texte officiel : elle garde chaque morceau compréhensible seul.
    """
    lignes = [seg for l in texte.split("\n") for seg in segmenter_ligne(l)]
    intro, reste = lignes[0], lignes[1:]
    groupes, courant = [], [intro]
    taille = len(intro)
    for ligne in reste:
        if taille + len(ligne) > SEUIL_CARACTERES and len(courant) > 1:
            groupes.append("\n".join(courant))
            courant, taille = [intro], len(intro)
        courant.append(ligne)
        taille += len(ligne) + 1
    groupes.append("\n".join(courant))
    return groupes


RE_DEFINITION = re.compile(r"^(\d+)\)\s+«")  # 5) «crypto-actif»: ...
MIN_DEFINITIONS = 5


def decouper_definitions(texte: str) -> list[tuple[str, str]] | None:
    """Si le paragraphe est une liste de définitions numérotées (« 5) «terme»: ... »), renvoie un passage par point,
    avec ses sous-items (a), b)). Sinon None. Une définition se cite par son point : « article 3, point 5 »."""
    lignes = texte.split("\n")
    debuts = [i for i, l in enumerate(lignes) if RE_DEFINITION.match(l)]
    if len(debuts) < MIN_DEFINITIONS:
        return None
    points = []
    for k, d in enumerate(debuts):
        fin = debuts[k + 1] if k + 1 < len(debuts) else len(lignes)
        points.append((RE_DEFINITION.match(lignes[d]).group(1), "\n".join(lignes[d:fin])))
    return points


def lignes_annexe(div) -> list[str]:
    """Lignes d'une annexe dans l'ordre du document : un paragraphe ou une ligne de tableau par ligne."""
    lignes = []
    for el in div.find_all(["p", "tr"]):
        if el.name == "p" and el.find_parent("td"):
            continue  # le texte d'une cellule est repris par sa ligne de tableau
        t = normaliser(" ".join(td.get_text(" ") for td in el.find_all("td"))) if el.name == "tr" else normaliser(el.get_text(" "))
        if t:
            lignes.append(t)
    return lignes


def decouper(chemin: Path, source_id: str, url: str) -> list[dict]:
    soupe = BeautifulSoup(chemin.read_text(encoding="utf-8"), "html.parser")
    passages = []

    for div in soupe.find_all("div", id=ID_ARTICLE):
        numero = int(ID_ARTICLE.match(div["id"]).group(1))
        titre_node = div.find("div", class_="eli-title")
        titre = normaliser(titre_node.get_text(" ")) if titre_node else ""
        paragraphes = [d for d in div.find_all("div", id=ID_PARAGRAPHE, recursive=False)]
        if paragraphes:
            parties = [(d["id"].split(".")[1].lstrip("0") or "0", texte_de(d)) for d in paragraphes]
        else:
            # Article sans paragraphe numéroté : on prend le texte brut hors titres.
            parties = [("", texte_de(div))]
        complet = "\n".join(t for _, t in parties)
        base = {
            "source": source_id,
            "type": "article",
            "article": str(numero),
            "titre": titre,
            "url": url,
        }
        if len(complet) <= SEUIL_CARACTERES:
            passages.append({**base, "chunk_id": f"{source_id}-art-{numero}", "paragraphe": "", "texte": complet})
        else:
            for p, texte in parties:
                definitions = decouper_definitions(texte) if len(texte) > SEUIL_CARACTERES else None
                if definitions:
                    for point, morceau in definitions:
                        passages.append({**base, "chunk_id": f"{source_id}-art-{numero}-p{p}-pt{point}",
                                         "paragraphe": p, "point": point, "texte": morceau})
                    continue
                morceaux = sous_decouper(texte) if len(texte) > SEUIL_CARACTERES else [texte]
                for k, morceau in enumerate(morceaux):
                    suffixe = f"-s{k + 1}" if len(morceaux) > 1 else ""
                    passages.append({**base, "chunk_id": f"{source_id}-art-{numero}-p{p}{suffixe}", "paragraphe": p, "texte": morceau})

    for div in soupe.find_all("div", id=ID_ANNEXE):
        numero = ID_ANNEXE.match(div["id"]).group(1)
        texte = "\n".join(lignes_annexe(div))
        morceaux = sous_decouper(texte) if len(texte) > SEUIL_CARACTERES else [texte]
        for k, morceau in enumerate(morceaux, start=1):
            suffixe = f"-s{k}" if len(morceaux) > 1 else ""
            passages.append({
                "source": source_id, "type": "annexe", "article": f"Annexe {numero}", "titre": "",
                "url": url, "chunk_id": f"{source_id}-anx-{numero}{suffixe}", "paragraphe": "", "texte": morceau,
            })
    return passages


def ecrire(passages: list[dict], sortie: Path) -> None:
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with sortie.open("w", encoding="utf-8") as f:
        for p in passages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    brut, source_id, url, sortie = sys.argv[1:5]
    res = decouper(Path(brut), source_id, url)
    ecrire(res, Path(sortie))
    print(f"{len(res)} passages écrits dans {sortie}")
