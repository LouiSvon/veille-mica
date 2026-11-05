"""Découpe l'impression PDF d'un texte Légifrance (ordonnance) en passages : un passage par article,
ou par groupes de blocs si l'article dépasse le seuil.

Structure attendue (constatée sur l'ordonnance 2024-936) : en-tête et pied de page répétés à chaque page,
« Titre ... : ... (Articles N à M) », puis « Article N » seul sur sa ligne, puis des blocs séparés par des lignes vides
(« I.- », « 1° », « a) » ...). Le texte avant le premier titre (les visas) devient un passage « visas ».
"""
import re

from app.chunking.pdf import normaliser

SEUIL_CARACTERES = 3500

RE_PIED = re.compile(r"^\s*\d+ sur \d+\s+\d{2}/\d{2}/\d{4}, \d{2}:\d{2}\s*$")
RE_TITRE = re.compile(r"^\s*(Titre\s+[IVX]+(?:ER)?\s*:.*)$")
RE_ARTICLE = re.compile(r"^\s*Article\s+(\d+)\s*$")


def _lignes_utiles(pages: list[str], prefixe_entete: str):
    """Itère (numéro de page, ligne) sans en-tête ni pied de page."""
    for numero, page in enumerate(pages, start=1):
        for ligne in page.split("\n"):
            if ligne.strip().startswith(prefixe_entete) or RE_PIED.match(ligne):
                continue
            yield numero, ligne.rstrip()


def _blocs(lignes: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Regroupe des lignes en blocs séparés par une ligne vide. Retourne (page du début, texte)."""
    blocs, courant, debut = [], [], 0
    for page, ligne in lignes:
        if not ligne.strip():
            if courant:
                blocs.append((debut, normaliser(" ".join(courant))))
                courant = []
            continue
        if not courant:
            debut = page
        courant.append(ligne.strip())
    if courant:
        blocs.append((debut, normaliser(" ".join(courant))))
    return blocs


def _grouper(blocs: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    groupes, courant, taille = [], [], 0
    for b in blocs:
        if courant and taille + len(b[1]) > SEUIL_CARACTERES:
            groupes.append(courant)
            courant, taille = [], 0
        courant.append(b)
        taille += len(b[1]) + 1
    if courant:
        groupes.append(courant)
    return groupes


def decouper_impression_legifrance(pages: list[str], source_id: str, url: str, prefixe_entete: str) -> list[dict]:
    titre_courant = ""
    article = None  # numéro de l'article en cours, None avant le premier titre (visas)
    zones: list[tuple[str, str, list[tuple[int, str]]]] = []  # (clé, titre, lignes)
    lignes_zone: list[tuple[int, str]] = []
    cle = "visas"
    for page, ligne in _lignes_utiles(pages, prefixe_entete):
        m_titre, m_art = RE_TITRE.match(ligne), RE_ARTICLE.match(ligne)
        if m_titre or m_art:
            zones.append((cle, titre_courant, lignes_zone))
            lignes_zone = []
            if m_titre:
                titre_courant = normaliser(m_titre.group(1))
                cle = "entre-titres"
            else:
                article = int(m_art.group(1))
                cle = f"art-{article}"
            continue
        lignes_zone.append((page, ligne))
    zones.append((cle, titre_courant, lignes_zone))

    passages: list[dict] = []
    for cle, titre, lignes in zones:
        blocs = _blocs(lignes)
        if not blocs or cle == "entre-titres" and not blocs:
            continue
        if cle == "entre-titres":
            # texte entre un titre et son premier article : ne devrait pas exister ; on ne le perd pas
            cle = "intertitre"
        groupes = _grouper(blocs)
        for k, g in enumerate(groupes, start=1):
            suffixe = f"-s{k}" if len(groupes) > 1 else ""
            est_art = cle.startswith("art-")
            passages.append({
                "source": source_id, "type": "article" if est_art else "preambule",
                "article": cle.split("-", 1)[1] if est_art else "visas",
                "paragraphe": "", "titre": titre, "url": url, "chunk_id": f"{source_id}-{cle}{suffixe}",
                "pages": sorted({p for p, _ in g}), "texte": "\n".join(t for _, t in g),
            })
    return passages
