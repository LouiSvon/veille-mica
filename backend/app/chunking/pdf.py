"""Découpe des PDF officiels en passages citables.

Deux cas :
- orientations à paragraphes numérotés (EBA/GL/2024/11) : un passage par paragraphe, avec le chemin de section ;
- document court sans numérotation (position AMF) : passages par blocs de texte.
Dans les deux cas, les notes de bas de page deviennent des passages à part (type "note") : elles
contiennent parfois une information utile (ex. un renvoi à une Q&A ESMA), donc on les garde et on les cite.

Prérequis système : pdftotext (poppler), par exemple `brew install poppler`.
"""
import re
import subprocess
from pathlib import Path

SEUIL_CARACTERES = 3500

RE_PAGE_NUM = re.compile(r"^\s*\d{1,3}\s*$")
RE_NOTE_DEBUT = re.compile(r"^\d{1,2}\s*$")  # numéro de note seul, collé à gauche
RE_TITRE_NUM = re.compile(r"^(\d+(?:\.\d+)+)\.\s+(\S.*)$")  # 4.1. Titre   4.2.1. Titre
RE_TITRE_N1 = re.compile(r"^(\d{1,2})\.\s+(\S.*)$")  # 2. Objet ...  (ou début de paragraphe)
RE_ITEM = re.compile(r"^\s*([a-z]\)|[ivx]+\)|-)\s")


def extraire_pages(chemin: Path) -> list[str]:
    sortie = subprocess.run(
        ["pdftotext", "-layout", str(chemin), "-"], check=True, capture_output=True, text=True
    ).stdout
    pages = sortie.split("\f")
    return pages[:-1] if pages and not pages[-1].strip() else pages


def normaliser(texte: str) -> str:
    return re.sub(r"\s+", " ", texte.replace("\xa0", " ")).strip()


def _separer_page(page: str, prefixe_entete: str | None) -> tuple[list[str], str]:
    """Retourne (lignes du corps, texte des notes de bas de page) pour une page."""
    lignes = page.split("\n")
    # En-tête courant : les lignes du début qui commencent comme l'en-tête, jusqu'à la première ligne vide après elles.
    if prefixe_entete:
        i = 0
        while i < len(lignes) and not lignes[i].strip():
            i += 1
        if i < len(lignes) and lignes[i].strip().startswith(prefixe_entete):
            while i < len(lignes) and lignes[i].strip():
                i += 1
            lignes = lignes[i:]
    # Numéro de page : dernière ligne non vide, composée d'un nombre seul.
    while lignes and not lignes[-1].strip():
        lignes.pop()
    if lignes and RE_PAGE_NUM.match(lignes[-1]):
        lignes.pop()
    # Notes de bas de page : à partir d'un numéro seul collé à gauche, dans la moitié basse de la page.
    debut_notes = None
    for idx, ligne in enumerate(lignes):
        if idx > len(lignes) * 0.4 and RE_NOTE_DEBUT.match(ligne) and idx + 1 < len(lignes) and lignes[idx + 1].startswith(" "):
            debut_notes = idx
            break
    if debut_notes is None:
        return lignes, ""
    return lignes[:debut_notes], normaliser(" ".join(lignes[debut_notes:]))


def _assembler(lignes: list[str]) -> str:
    """Joint les lignes d'un paragraphe ; chaque item de liste (a), b), tiret) commence une nouvelle ligne."""
    morceaux: list[str] = []
    for brut in lignes:
        s = brut.strip()
        if not s:
            continue
        if RE_ITEM.match(brut) and morceaux:
            morceaux.append("\n" + s)
        else:
            morceaux.append(" " + s if morceaux and not morceaux[-1].endswith("\n") else s)
    return normaliser_lignes("".join(morceaux))


def normaliser_lignes(texte: str) -> str:
    return "\n".join(normaliser(l) for l in texte.split("\n") if l.strip())


def decouper_orientations(pages: list[str], source_id: str, url: str, prefixe_entete: str | None = None) -> list[dict]:
    passages: list[dict] = []
    dernier = 0  # numéro du dernier paragraphe ouvert
    titres: dict[int, str] = {}  # niveau -> titre courant
    sous_titre = ""
    courant: dict | None = None

    def fermer():
        nonlocal courant
        if courant is not None:
            courant["texte"] = _assembler(courant.pop("_lignes"))
            passages.append(courant)
            courant = None

    for numero_page, page in enumerate(pages, start=1):
        corps, notes = _separer_page(page, prefixe_entete if numero_page > 1 else None)
        i = 0
        while i < len(corps):
            ligne = corps[i]
            s = ligne.strip()
            if not s:
                i += 1
                continue
            # Titre numéroté de niveau 2 ou plus : 4.1. Titre
            m = RE_TITRE_NUM.match(s)
            if m and not ligne.startswith("  "):
                fermer()
                titre = s
                i += 1
                while i < len(corps) and corps[i].strip() and corps[i].startswith("  "):
                    titre += " " + corps[i].strip()
                    i += 1
                niveau = m.group(1).count(".") + 1
                titres[niveau] = normaliser(titre)
                for k in [k for k in titres if k > niveau]:
                    del titres[k]
                sous_titre = ""
                continue
            m = RE_TITRE_N1.match(s)
            if m and not ligne.startswith("  "):
                n = int(m.group(1))
                suivant = next((corps[j].strip() for j in range(i + 1, len(corps)) if corps[j].strip()), "")
                attendu = n == dernier + 1
                # Un paragraphe est numéroté dans l'ordre. Un titre de niveau 1 ne l'est pas, sauf au tout début,
                # où "1. Titre" précède "1. Premier paragraphe" : le titre est alors suivi d'un intertitre court sans numéro.
                est_intertitre = bool(suivant) and len(suivant) < 70 and not re.match(r"^\d", suivant) and not suivant.endswith((".", ":", ";"))
                if not attendu or (dernier == 0 and est_intertitre and not s.endswith(".")):
                    fermer()
                    titre = s
                    i += 1
                    while i < len(corps) and corps[i].strip() and corps[i].startswith("  "):
                        titre += " " + corps[i].strip()
                        i += 1
                    titres.clear()
                    titres[1] = normaliser(titre)
                    sous_titre = ""
                    continue
                fermer()
                dernier = n
                courant = {
                    "source": source_id, "type": "paragraphe", "article": f"paragraphe {n}",
                    "paragraphe": str(n), "titre": " > ".join(
                        [titres[k] for k in sorted(titres)] + ([sous_titre] if sous_titre else [])
                    ),
                    "url": url, "chunk_id": f"{source_id}-par-{n}", "pages": [numero_page],
                    "_lignes": [s[len(m.group(1)) + 1:]],
                }
                i += 1
                continue
            # Intertitre non numéroté : ligne courte, sans ponctuation finale, suivie du prochain paragraphe numéroté.
            suivant = next((corps[j].strip() for j in range(i + 1, len(corps)) if corps[j].strip()), "")
            if (len(s) < 70 and not s.endswith((".", ":", ";", ",")) and not RE_ITEM.match(ligne)
                    and re.match(rf"^{dernier + 1}\.\s", suivant)):
                fermer()
                sous_titre = normaliser(s)
                i += 1
                continue
            if courant is not None:
                courant["_lignes"].append(ligne)
                if numero_page not in courant["pages"]:
                    courant["pages"].append(numero_page)
            i += 1
        if notes:
            passages.append({
                "source": source_id, "type": "note", "article": f"notes de bas de page, page {numero_page}",
                "paragraphe": "", "titre": "", "url": url, "chunk_id": f"{source_id}-p{numero_page}-notes",
                "pages": [numero_page], "texte": notes,
            })
    fermer()
    return passages


def decouper_document_court(pages: list[str], source_id: str, url: str, titre: str) -> list[dict]:
    """Document sans numérotation : blocs séparés par une ligne vide, regroupés jusqu'au seuil. Notes à part."""
    passages: list[dict] = []
    blocs: list[tuple[int, str]] = []
    for numero_page, page in enumerate(pages, start=1):
        corps, notes = _separer_page(page, None)
        for bloc in re.split(r"\n\s*\n", "\n".join(corps)):
            texte = _assembler(bloc.split("\n"))
            if texte:
                blocs.append((numero_page, texte))
        if notes:
            passages.append({
                "source": source_id, "type": "note", "article": f"notes de bas de page, page {numero_page}",
                "paragraphe": "", "titre": titre, "url": url, "chunk_id": f"{source_id}-p{numero_page}-notes",
                "pages": [numero_page], "texte": notes,
            })
    groupe: list[tuple[int, str]] = []
    taille = 0
    k = 0

    def vider():
        nonlocal groupe, taille, k
        if groupe:
            k += 1
            passages.append({
                "source": source_id, "type": "bloc", "article": f"bloc {k}", "paragraphe": str(k), "titre": titre,
                "url": url, "chunk_id": f"{source_id}-bloc-{k}", "pages": sorted({p for p, _ in groupe}),
                "texte": "\n".join(t for _, t in groupe),
            })
            groupe, taille = [], 0

    for page, texte in blocs:
        if taille + len(texte) > SEUIL_CARACTERES:
            vider()
        groupe.append((page, texte))
        taille += len(texte)
    vider()
    # Les passages de notes viennent après les blocs dans la liste, pour garder un ordre de lecture stable.
    return sorted(passages, key=lambda p: p["type"] == "note")
