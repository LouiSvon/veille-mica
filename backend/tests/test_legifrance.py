import re
from pathlib import Path

import pytest

from app.chunking.legifrance import RE_ARTICLE, RE_PIED, RE_TITRE, _lignes_utiles, decouper_impression_legifrance
from app.chunking.pdf import extraire_pages, normaliser

PDF = Path(__file__).resolve().parents[2] / "data" / "raw" / "ordonnance-2024-936-fr.pdf"
ENTETE = "Ordonnance n° 2024-936 du 15 octobre 2024 relative aux marchés de c..."
absent = pytest.mark.skipif(not PDF.exists(), reason="PDF brut absent (data/raw non versionné)")

PAGE1 = """Ordonnance n° 2024-936 du 15 octobre 2024 relative aux marchés de c...   https://exemple

           Le Président de la République,
           Vu la Constitution ;

1 sur 2                                         05/11/2026, 16:11
"""
PAGE2 = """Ordonnance n° 2024-936 du 15 octobre 2024 relative aux marchés de c...   https://exemple

       Titre IER : DISPOSITIONS GÉNÉRALES (Articles 1 à 2)
       Article 1

       I.-Premier alinéa
       qui continue.


       II.-Second alinéa.

       Article 2

       Texte de l'article deux.

2 sur 2                                         05/11/2026, 16:11
"""


def test_synthetique_visas_articles_titre_en_tete_et_pied_retires():
    p = decouper_impression_legifrance([PAGE1, PAGE2], "o", "u", ENTETE)
    ids = [c["chunk_id"] for c in p]
    assert ids == ["o-visas", "o-art-1", "o-art-2"]
    par = {c["chunk_id"]: c for c in p}
    assert par["o-visas"]["texte"] == "Le Président de la République, Vu la Constitution ;"
    assert par["o-art-1"]["texte"] == "I.-Premier alinéa qui continue.\nII.-Second alinéa."
    assert par["o-art-1"]["titre"].startswith("Titre IER : DISPOSITIONS GÉNÉRALES")
    assert par["o-art-2"]["texte"] == "Texte de l'article deux."
    tout = " ".join(c["texte"] for c in p)
    assert "05/11/2026" not in tout and "https://exemple" not in tout and "sur 2" not in tout


def test_synthetique_article_long_est_decoupe_sans_perte():
    long_blocs = "\n\n".join(f"{i}° " + "mot " * 200 for i in range(1, 8))
    page = f"       Titre IER : T (Articles 1 à 1)\n       Article 1\n\n{long_blocs}\n"
    p = decouper_impression_legifrance([page], "o", "u", ENTETE)
    assert len(p) > 1 and all(c["chunk_id"].startswith("o-art-1-s") for c in p)
    assert all(len(c["texte"]) <= 3500 + 1000 for c in p)
    restitue = " ".join(c["texte"] for c in p)
    assert all(f"{i}° mot" in restitue for i in range(1, 8))


@absent
def test_ordonnance_50_articles_contigus():
    p = decouper_impression_legifrance(extraire_pages(PDF), "ord", "u", ENTETE)
    nums = sorted({int(c["article"]) for c in p if c["type"] == "article"})
    assert nums == list(range(1, 51))
    assert [c["chunk_id"] for c in p][0] == "ord-visas"


@absent
def test_ordonnance_article_49_dates_d_entree_en_vigueur():
    p = {c["chunk_id"]: c for c in decouper_impression_legifrance(extraire_pages(PDF), "ord", "u", ENTETE)}
    a49 = p["ord-art-49"]["texte"]
    assert "entrent en vigueur le 30 décembre 2024" in a49
    assert "Les articles 24 à 33 et 46 à 48 entrent en vigueur le 1er juillet 2026" in a49
    assert p["ord-art-49"]["titre"].startswith("Titre III : DISPOSITIONS FINALES")


@absent
def test_ordonnance_aucune_trace_d_en_tete_ni_de_pied():
    for c in decouper_impression_legifrance(extraire_pages(PDF), "ord", "u", ENTETE):
        assert "sur 71" not in c["texte"] and "05/11/2026, 16:11" not in c["texte"]
        assert "legifrance.gouv.fr/jorf/id/JORFTEXT" not in c["texte"]


def lignes_perdues(pages, passages):
    """Lignes de contenu de l'impression absentes des passages (hors titres et lignes « Article N »)."""
    tout = normaliser(" ".join(c["texte"] for c in passages))
    perdues = []
    for page, ligne in _lignes_utiles(pages, ENTETE):
        s = normaliser(ligne)
        if not s or RE_TITRE.match(ligne) or RE_ARTICLE.match(ligne):
            continue
        if s not in tout:
            perdues.append((page, s))
    return perdues


@absent
def test_ordonnance_aucune_ligne_perdue():
    pages = extraire_pages(PDF)
    assert lignes_perdues(pages, decouper_impression_legifrance(pages, "ord", "u", ENTETE)) == []


@absent
def test_le_detecteur_signale_un_article_retire():
    """Cas positif : sans l'article 49, la ligne sur le 1er juillet 2026 est signalée comme perdue."""
    pages = extraire_pages(PDF)
    p = [c for c in decouper_impression_legifrance(pages, "ord", "u", ENTETE) if c["chunk_id"] != "ord-art-49"]
    assert any("1er juillet 2026" in s for _, s in lignes_perdues(pages, p))
