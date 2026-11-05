"""Construit data/processed/chunks.jsonl à partir du registre data/sources.yaml.

Avant de découper un texte, on vérifie que son empreinte est celle du registre : un texte modifié
ou remplacé sans mise à jour du registre arrête la construction.

Usage : python -m app.chunking.construire
"""
import hashlib
import json
import sys
from pathlib import Path

import yaml

from app.chunking.decouper import decouper as decouper_xhtml
from app.chunking.legifrance import decouper_impression_legifrance
from app.chunking.pdf import decouper_document_court, decouper_orientations, extraire_pages

RACINE = Path(__file__).resolve().parents[3]
REGISTRE = RACINE / "data" / "sources.yaml"
BRUT = RACINE / "data" / "raw"
SORTIE = RACINE / "data" / "processed" / "chunks.jsonl"

# Prefixe de l'en-tête courant à retirer de chaque page, par source (propre à la mise en page de chaque PDF).
ENTETES = {"eba-gl-2024-11": "ORIENTATIONS SUR LES EXIGENCES", "amf-doc-2024-08": "Position AMF - DOC-2024-08",
           "ordonnance-2024-936": "Ordonnance n° 2024-936 du 15 octobre 2024 relative aux marchés de c..."}
STATUTS_PRETS = {"telecharge_et_lu"}


class EmpreinteInvalide(Exception):
    pass


def sha256_fichier(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def passages_de(source: dict, brut: Path = BRUT) -> list[dict]:
    chemin = brut / source["fichier"]
    if sha256_fichier(chemin) != source["sha256"]:
        raise EmpreinteInvalide(f"{source['id']} : l'empreinte de {chemin.name} ne correspond pas au registre")
    sid, url = source["id"], source["url_officielle"]
    if source["format"] == "xhtml":
        res = decouper_xhtml(chemin, sid, url)
    elif sid == "ordonnance-2024-936":
        res = decouper_impression_legifrance(extraire_pages(chemin), sid, url, ENTETES[sid])
    elif sid == "eba-gl-2024-11":
        res = decouper_orientations(extraire_pages(chemin), sid, url, ENTETES[sid])
    elif source["format"] == "pdf":
        res = decouper_document_court(extraire_pages(chemin), sid, url, source["titre"], ENTETES.get(sid))
    else:
        raise ValueError(f"format non géré pour {sid} : {source['format']}")
    for p in res:
        p.update({
            "source_titre": source["titre"], "identifiant": source["identifiant"],
            "contraignant": source["contraignant"], "langue": source["langue"],
            "version": source["version"], "date_consultation": source["date_consultation"],
        })
    return res


def construire(registre: Path = REGISTRE, brut: Path = BRUT, sortie: Path = SORTIE) -> dict[str, int]:
    sources = yaml.safe_load(registre.read_text(encoding="utf-8"))["sources"]
    comptes: dict[str, int] = {}
    tout: list[dict] = []
    for s in sources:
        if s["statut"] not in STATUTS_PRETS:
            continue
        res = passages_de(s, brut)
        comptes[s["id"]] = len(res)
        tout.extend(res)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with sortie.open("w", encoding="utf-8") as f:
        for p in tout:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    return comptes


if __name__ == "__main__":
    for sid, n in construire().items():
        print(f"{sid}: {n} passages")
    print(f"écrit dans {SORTIE}", file=sys.stderr)
