from pathlib import Path

import pytest

from app.chunking.pdf import (
    decouper_document_court, decouper_orientations, extraire_pages,
)

RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
EBA = RAW / "eba-gl-2024-11-fr.pdf"
AMF = RAW / "amf-doc-2024-08-fr.pdf"
ENTETE = "ORIENTATIONS SUR LES EXIGENCES"

PAGE1 = """Orientations

1. Obligations en matière de conformité

Statut des présentes orientations
1. Le présent document contient des orientations.
   Suite du premier paragraphe.

2. Deuxième paragraphe:

          a) premier item;

          b) second item.

1
 Note numéro un, texte officiel.
                                   1
"""

PAGE2 = """ORIENTATIONS SUR LES EXIGENCES EN MATIÈRE
FONDS ET CERTAINS

2. Objet et champ

3. Troisième paragraphe qui continue
   sur la ligne suivante.

4.1. Dispositions générales
4. Quatrième paragraphe sous un titre numéroté.
                                   2
"""


def test_synthetique_numerotation_titres_notes_entete():
    p = decouper_orientations([PAGE1, PAGE2], "x", "u", ENTETE)
    par = {c["paragraphe"]: c for c in p if c["type"] == "paragraphe"}
    assert sorted(par, key=int) == ["1", "2", "3", "4"]
    assert par["1"]["texte"] == "Le présent document contient des orientations. Suite du premier paragraphe."
    assert par["2"]["texte"] == "Deuxième paragraphe:\na) premier item;\nb) second item."
    assert par["3"]["texte"] == "Troisième paragraphe qui continue sur la ligne suivante."
    assert par["1"]["titre"].startswith("1. Obligations") and "Statut des présentes orientations" in par["1"]["titre"]
    assert par["3"]["titre"] == "2. Objet et champ"
    assert par["4"]["titre"] == "2. Objet et champ > 4.1. Dispositions générales"
    notes = [c for c in p if c["type"] == "note"]
    assert len(notes) == 1 and notes[0]["texte"] == "1 Note numéro un, texte officiel."
    # Cas négatif : ni l'en-tête courant ni les numéros de page ne fuient dans le texte.
    tout = " ".join(c["texte"] for c in p)
    assert "ORIENTATIONS SUR LES EXIGENCES" not in tout and "FONDS ET CERTAINS" not in tout


@pytest.mark.skipif(not EBA.exists(), reason="PDF brut absent (data/raw non versionné)")
def test_eba_94_paragraphes_contigus():
    p = decouper_orientations(extraire_pages(EBA), "eba", "u", ENTETE)
    nums = [int(c["paragraphe"]) for c in p if c["type"] == "paragraphe"]
    assert nums == list(range(1, 95))


@pytest.mark.skipif(not EBA.exists(), reason="PDF brut absent (data/raw non versionné)")
def test_eba_paragraphes_cles():
    par = {c["paragraphe"]: c for c in decouper_orientations(extraire_pages(EBA), "eba", "u", ENTETE) if c["type"] == "paragraphe"}
    assert par["1"]["texte"].startswith("Le présent document contient des orientations")
    assert "27.11.2024" in par["3"]["texte"]
    assert par["10"]["texte"] == "Les présentes orientations s’appliquent à compter du 30 décembre 2024."
    assert "4.1. Dispositions générales" in par["12"]["titre"]
    assert par["12"]["titre"].startswith("4. Exigences en matière d’information")


@pytest.mark.skipif(not EBA.exists(), reason="PDF brut absent (data/raw non versionné)")
def test_eba_pas_d_entete_ni_de_numero_de_page_dans_le_texte():
    p = decouper_orientations(extraire_pages(EBA), "eba", "u", ENTETE)
    for c in p:
        assert "ORIENTATIONS SUR LES EXIGENCES EN MATIÈRE D’INFORMATION" not in c["texte"]
        assert not c["texte"].rstrip().split("\n")[-1].strip().isdigit()


@pytest.mark.skipif(not EBA.exists(), reason="PDF brut absent (data/raw non versionné)")
def test_eba_notes_de_bas_de_page_conservees():
    notes = [c for c in decouper_orientations(extraire_pages(EBA), "eba", "u", ENTETE) if c["type"] == "note"]
    assert any("1093/2010" in c["texte"] for c in notes)


@pytest.mark.skipif(not AMF.exists(), reason="PDF brut absent (data/raw non versionné)")
def test_amf_corps_et_note_esma_qa_2295():
    p = decouper_document_court(extraire_pages(AMF), "amf", "u", "Position AMF DOC-2024-08", "Position AMF - DOC-2024-08")
    corps = " ".join(c["texte"] for c in p if c["type"] == "bloc")
    notes = " ".join(c["texte"] for c in p if c["type"] == "note")
    assert "applicables à compter du 30 décembre 2024" in corps
    assert "ESMA_QA_2295" in notes and "ESMA_QA_2295" not in corps


@pytest.mark.skipif(not AMF.exists(), reason="PDF brut absent (data/raw non versionné)")
def test_amf_en_tete_de_page_2_retire_et_phrase_continue():
    p = decouper_document_court(extraire_pages(AMF), "amf", "u", "t", "Position AMF - DOC-2024-08")
    corps = " ".join(c["texte"] for c in p if c["type"] == "bloc")
    assert "Position AMF - DOC-2024-08 –" not in corps
    assert "exclusivement les services de gestion de portefeuille de crypto-actifs ou de conseils en crypto-actifs et ayant leur siège" in corps.replace("\n", " ")
