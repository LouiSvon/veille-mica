import json
import re
from pathlib import Path

import pytest
import yaml

from app.chunking import construire as c
from app.chunking.pdf import _separer_page, extraire_pages, decouper_orientations, normaliser

RAW = c.BRUT
PRET = all((RAW / f).exists() for f in ("mica-2023-1114-fr.xhtml", "tfr-2023-1113-fr.xhtml", "eba-gl-2024-11-fr.pdf", "amf-doc-2024-08-fr.pdf", "ordonnance-2024-936-fr.pdf"))
absent = pytest.mark.skipif(not PRET, reason="textes bruts absents (data/raw non versionné)")


@absent
def test_construction_complete_et_metadonnees(tmp_path):
    sortie = tmp_path / "chunks.jsonl"
    comptes = c.construire(sortie=sortie)
    assert set(comptes) == {"mica", "tfr", "eba-gl-2024-11", "amf-doc-2024-08", "ordonnance-2024-936"}
    lignes = [json.loads(l) for l in sortie.read_text(encoding="utf-8").splitlines()]
    assert len(lignes) == sum(comptes.values())
    ids = [l["chunk_id"] for l in lignes]
    assert len(ids) == len(set(ids)), "identifiants de passages en double"
    for l in lignes:
        assert l["texte"].strip() and l["date_consultation"] == "2026-11-05" and l["url"].startswith("https://")
        assert l["contraignant"] in (True, False, "a_fournir")


@absent
def test_empreinte_differente_arrete_la_construction(tmp_path):
    sources = yaml.safe_load(c.REGISTRE.read_text(encoding="utf-8"))["sources"]
    s = dict(next(x for x in sources if x["id"] == "tfr"))
    s["sha256"] = "0" * 64
    with pytest.raises(c.EmpreinteInvalide):
        c.passages_de(s)


def lignes_perdues(pages, passages, entete):
    """Lignes du corps du PDF qui ne sont ni dans un passage ni dans un titre de section."""
    tout = normaliser(" ".join(x["texte"] for x in passages))
    titres = {normaliser(t) for x in passages for t in x["titre"].split(" > ") if t.strip()}
    perdues = []
    for n, page in enumerate(pages, 1):
        if n == 1:
            continue  # page de titre : pas de contenu normatif
        corps, _ = _separer_page(page, entete if n > 1 else None)
        for ligne in corps:
            # Le numéro de paragraphe ("12. ") est conservé dans le champ "paragraphe", pas dans le texte.
            s = re.sub(r"^\d{1,2}\.\s+", "", normaliser(ligne))
            if s and s not in tout and not any(s in t or t in s for t in titres):
                perdues.append((n, s))
    return perdues


@absent
def test_eba_aucune_ligne_du_corps_n_est_perdue():
    pages = extraire_pages(RAW / "eba-gl-2024-11-fr.pdf")
    entete = c.ENTETES["eba-gl-2024-11"]
    p = decouper_orientations(pages, "eba", "u", entete)
    assert lignes_perdues(pages, p, entete) == []


@absent
def test_le_detecteur_de_pertes_signale_un_passage_retire():
    """Cas positif du détecteur : sans le paragraphe 10, sa ligne est signalée comme perdue."""
    pages = extraire_pages(RAW / "eba-gl-2024-11-fr.pdf")
    entete = c.ENTETES["eba-gl-2024-11"]
    p = [x for x in decouper_orientations(pages, "eba", "u", entete) if x["chunk_id"] != "eba-par-10"]
    perdues = lignes_perdues(pages, p, entete)
    assert any("30 décembre 2024" in s for _, s in perdues)
