from pathlib import Path

import pytest

from src.decoupage.decouper import decouper, SEUIL_CARACTERES

BRUT = Path(__file__).resolve().parent.parent / "sources" / "brut"
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


@pytest.mark.skipif(not MICA.exists(), reason="texte brut absent (sources/brut non versionné)")
def test_mica_149_articles_et_6_annexes():
    p = decouper(MICA, "mica", "u")
    articles = {c["article"] for c in p if c["type"] == "article"}
    assert articles == {str(n) for n in range(1, 150)}
    assert len([c for c in p if c["type"] == "annexe"]) == 6


@pytest.mark.skipif(not MICA.exists(), reason="texte brut absent (sources/brut non versionné)")
def test_mica_article_143_cite_le_1er_juillet_2026():
    p = {c["chunk_id"]: c for c in decouper(MICA, "mica", "u")}
    texte = p["mica-art-143"]["texte"] if "mica-art-143" in p else p["mica-art-143-p3"]["texte"]
    assert "jusqu’au 1 er juillet 2026" in texte


@pytest.mark.skipif(not MICA.exists(), reason="texte brut absent (sources/brut non versionné)")
def test_mica_aucun_passage_vide_ni_geant():
    p = decouper(MICA, "mica", "u")
    assert all(len(c["texte"]) > 20 for c in p)
    # Un article numéroté sans paragraphes reste un passage unique : on borne l'énorme pour détecter une erreur d'analyse.
    assert max(len(c["texte"]) for c in p if c["type"] == "article") < 5000


@pytest.mark.skipif(not TFR.exists(), reason="texte brut absent (sources/brut non versionné)")
def test_tfr_40_articles():
    articles = {c["article"] for c in decouper(TFR, "tfr", "u") if c["type"] == "article"}
    assert articles == {str(n) for n in range(1, 41)}


@pytest.mark.skipif(not MICA.exists(), reason="texte brut absent (sources/brut non versionné)")
def test_mica_article_3_decoupe_et_garde_les_definitions():
    p = [c for c in decouper(MICA, "mica", "u") if c["article"] == "3" and c["paragraphe"] == "1"]
    assert len(p) > 1
    tout = "\n".join(c["texte"] for c in p)
    assert "«crypto-actif»" in tout
    assert all(c["texte"].startswith("1. Aux fins du présent règlement") for c in p)
