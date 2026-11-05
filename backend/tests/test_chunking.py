from pathlib import Path

import pytest

from app.chunking.decouper import decouper, SEUIL_CARACTERES

BRUT = Path(__file__).resolve().parents[2] / "data" / "raw"
MICA = BRUT / "mica-2023-1114-fr.xhtml"
TFR = BRUT / "tfr-2023-1113-fr.xhtml"

XHTML_MINI = """<html><body>
<div class="eli-subdivision" id="art_1"><p class="oj-ti-art">Article 1</p>
 <div class="eli-title"><p class="oj-sti-art">Objet</p></div>
 <div id="001.001"><p class="oj-normal">1.   Premier paragraphe.</p></div>
 <div id="001.002"><p class="oj-normal">2.   Liste:</p>
  <table><tbody><tr><td><p>a)</p></td><td><p>premier item;</p></td></tr></tbody></table></div>
</div>
<div class="eli-subdivision" id="art_2"><p class="oj-ti-art">Article 2</p>
 <div class="eli-title"><p class="oj-sti-art">Long</p></div>
 <div id="002.001"><p class="oj-normal">%s</p></div>
 <div id="002.002"><p class="oj-normal">Fin.</p></div>
</div>
<div id="anx_I"><p>ANNEXE I</p><p>Contenu annexe</p></div>
</body></html>""" % ("mot " * (SEUIL_CARACTERES // 4 + 10))


def test_mini_article_court_non_decoupe(tmp_path):
    f = tmp_path / "m.xhtml"
    f.write_text(XHTML_MINI, encoding="utf-8")
    p = {c["chunk_id"]: c for c in decouper(f, "x", "u")}
    assert p["x-art-1"]["texte"] == "1. Premier paragraphe.\n2. Liste:\na) premier item;"
    assert p["x-art-1"]["titre"] == "Objet"


def test_mini_article_long_decoupe_par_paragraphe(tmp_path):
    f = tmp_path / "m.xhtml"
    f.write_text(XHTML_MINI, encoding="utf-8")
    ids = [c["chunk_id"] for c in decouper(f, "x", "u")]
    assert "x-art-2-p1" in ids and "x-art-2-p2" in ids and "x-art-2" not in ids
    assert "x-anx-I" in ids


@pytest.mark.skipif(not MICA.exists(), reason="texte brut absent (data/raw non versionné)")
def test_mica_149_articles_et_6_annexes():
    p = decouper(MICA, "mica", "u")
    articles = {c["article"] for c in p if c["type"] == "article"}
    assert articles == {str(n) for n in range(1, 150)}
    assert {c["article"] for c in p if c["type"] == "annexe"} == {f"Annexe {n}" for n in ("I", "II", "III", "IV", "V", "VI")}


@pytest.mark.skipif(not MICA.exists(), reason="texte brut absent (data/raw non versionné)")
def test_mica_article_143_cite_le_1er_juillet_2026():
    p = {c["chunk_id"]: c for c in decouper(MICA, "mica", "u")}
    texte = p["mica-art-143"]["texte"] if "mica-art-143" in p else p["mica-art-143-p3"]["texte"]
    assert "jusqu’au 1 er juillet 2026" in texte


@pytest.mark.skipif(not MICA.exists(), reason="texte brut absent (data/raw non versionné)")
def test_mica_aucun_passage_vide_ni_geant():
    p = decouper(MICA, "mica", "u")
    assert all(len(c["texte"]) > 20 for c in p)
    # Borne anti-erreur d'analyse. Le plus long passage légitime est la définition 33 (État membre d'origine, 5 707 car.),
    # une seule définition avec ses sous-points a) à f).
    assert max(len(c["texte"]) for c in p if c["type"] == "article") < 8000


@pytest.mark.skipif(not TFR.exists(), reason="texte brut absent (data/raw non versionné)")
def test_tfr_40_articles():
    articles = {c["article"] for c in decouper(TFR, "tfr", "u") if c["type"] == "article"}
    assert articles == {str(n) for n in range(1, 41)}


@pytest.mark.skipif(not MICA.exists(), reason="texte brut absent (data/raw non versionné)")
def test_mica_article_3_une_definition_par_point():
    p = [c for c in decouper(MICA, "mica", "u") if c["article"] == "3" and c.get("point")]
    points = [int(c["point"]) for c in p]
    assert points == list(range(1, len(points) + 1)) and len(points) >= 45
    par_point = {c["point"]: c for c in p}
    assert par_point["5"]["texte"].startswith("5) «crypto-actif»: une représentation numérique d’une valeur")
    assert "«jeton de monnaie électronique»" in par_point["7"]["texte"]
    assert par_point["5"]["chunk_id"] == "mica-art-3-p1-pt5"
    # Aucune définition n'est mélangée à la suivante.
    assert "«jeton se référant" not in par_point["5"]["texte"]


@pytest.mark.skipif(not TFR.exists(), reason="texte brut absent (data/raw non versionné)")
def test_tfr_article_3_definitions_par_point():
    p = [c for c in decouper(TFR, "tfr", "u") if c["article"] == "3" and c.get("point")]
    assert [int(c["point"]) for c in p] == list(range(1, len(p) + 1)) and len(p) >= 20


def test_decouper_definitions_ne_decoupe_pas_une_liste_ordinaire():
    from app.chunking.decouper import decouper_definitions
    assert decouper_definitions("1. Intro:\na) item;\nb) item.") is None
    liste = "1. Intro:\n" + "\n".join(f"{i}) «terme{i}»: définition {i}" for i in range(1, 7))
    res = decouper_definitions(liste)
    assert [pt for pt, _ in res] == ["1", "2", "3", "4", "5", "6"]
    assert res[2][1] == "3) «terme3»: définition 3"


@pytest.mark.skipif(not MICA.exists(), reason="texte brut absent (data/raw non versionné)")
def test_aucun_passage_mica_ne_depasse_6000_caracteres():
    """Les annexes (jusqu'à 27 600 caractères) sont découpées : un passage géant fausserait la recherche et dépasserait le contexte."""
    longs = [(c["chunk_id"], len(c["texte"])) for c in decouper(MICA, "mica", "u") if len(c["texte"]) > 6000]
    assert longs == []


@pytest.mark.skipif(not TFR.exists(), reason="texte brut absent (data/raw non versionné)")
def test_aucun_passage_tfr_ne_depasse_6000_caracteres():
    longs = [(c["chunk_id"], len(c["texte"])) for c in decouper(TFR, "tfr", "u") if len(c["texte"]) > 6000]
    assert longs == []


@pytest.mark.skipif(not MICA.exists(), reason="texte brut absent (data/raw non versionné)")
def test_annexes_decoupees_sans_perdre_un_mot():
    from bs4 import BeautifulSoup
    soupe = BeautifulSoup(MICA.read_text(encoding="utf-8"), "html.parser")
    p = decouper(MICA, "mica", "u")
    for n in ("I", "II", "III", "V", "VI"):
        original = set(soupe.find("div", id=f"anx_{n}").get_text(" ").split())
        restitue = set(" ".join(c["texte"] for c in p if c["chunk_id"].startswith(f"mica-anx-{n}")).split())
        assert original <= restitue, f"annexe {n} : mots perdus {sorted(original - restitue)[:5]}"


def test_segmenter_ligne_coupe_aux_fins_de_phrase_sans_rien_perdre():
    from app.chunking.decouper import segmenter_ligne
    ligne = " ".join(f"Phrase numéro {i} qui se termine ici;" for i in range(200))
    morceaux = segmenter_ligne(ligne, 500)
    assert len(morceaux) > 1 and all(len(m) <= 500 for m in morceaux)
    assert " ".join(morceaux) == ligne
    assert segmenter_ligne("courte ligne", 500) == ["courte ligne"]
    assert segmenter_ligne("x" * 900, 500) == ["x" * 900]  # aucune fin de phrase : ligne gardée entière
