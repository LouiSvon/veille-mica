import hashlib
import importlib.util
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("telecharger", RACINE / "scripts" / "telecharger.py")
tel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tel)


def source(tmp_path, contenu: bytes, sha="a_fournir"):
    f = tmp_path / "src.bin"
    f.write_bytes(contenu)
    return {"id": "x", "url_telechargement": f.as_uri(), "en_tetes": {}, "fichier": "x.bin", "sha256": sha}


def test_telechargement_et_hash_identique(tmp_path):
    contenu = b"texte officiel"
    s = source(tmp_path, contenu, hashlib.sha256(contenu).hexdigest())
    sortie = tmp_path / "raw"
    assert "identique" in tel.traiter(s, sortie, verifier_seulement=False)
    assert (sortie / "x.bin").read_bytes() == contenu


def test_hash_different_est_signale(tmp_path):
    s = source(tmp_path, b"texte modifie", hashlib.sha256(b"autre").hexdigest())
    assert "DIFFERENT" in tel.traiter(s, tmp_path / "raw", verifier_seulement=False)


def test_reponse_vide_est_une_erreur(tmp_path):
    s = source(tmp_path, b"")
    with pytest.raises(tel.TelechargementInvalide):
        tel.traiter(s, tmp_path / "raw", verifier_seulement=False)


def test_verifier_sans_telecharger(tmp_path):
    contenu = b"abc"
    s = source(tmp_path, contenu, hashlib.sha256(contenu).hexdigest())
    raw = tmp_path / "raw"
    assert tel.traiter(s, raw, verifier_seulement=True) == "absent"
    raw.mkdir()
    (raw / "x.bin").write_bytes(contenu)
    assert tel.traiter(s, raw, verifier_seulement=True) == "identique"
    (raw / "x.bin").write_bytes(b"corrompu")
    assert tel.traiter(s, raw, verifier_seulement=True) == "DIFFERENT"


def test_url_a_fournir_est_ignoree(tmp_path):
    s = {"id": "y", "url_telechargement": "a_fournir", "fichier": "y.pdf", "sha256": "a_fournir", "en_tetes": {}}
    assert "ignoré" in tel.traiter(s, tmp_path, verifier_seulement=False)


def test_registre_coherent():
    sources = yaml.safe_load((RACINE / "data" / "sources.yaml").read_text(encoding="utf-8"))["sources"]
    ids = [s["id"] for s in sources]
    assert len(ids) == len(set(ids))
    for s in sources:
        if s["statut"] == "telecharge_et_lu":
            assert len(s["sha256"]) == 64 and s["date_consultation"] != "a_fournir"


def test_un_fichier_present_et_identique_n_est_pas_retelecharge(tmp_path):
    """« Télécharge ce qui manque » : la source contient un autre contenu ; s'il était retéléchargé, le fichier local changerait."""
    local = b"contenu local"
    s = source(tmp_path, b"contenu distant different", hashlib.sha256(local).hexdigest())
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "x.bin").write_bytes(local)
    assert "non retéléchargé" in tel.traiter(s, raw, verifier_seulement=False)
    assert (raw / "x.bin").read_bytes() == local


def test_un_fichier_present_mais_different_est_retelecharge(tmp_path):
    local, distant = b"contenu local modifie", b"contenu distant"
    s = source(tmp_path, distant, hashlib.sha256(distant).hexdigest())
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "x.bin").write_bytes(local)
    assert "identique" in tel.traiter(s, raw, verifier_seulement=False)
    assert (raw / "x.bin").read_bytes() == distant


def test_forcer_retelecharge_meme_un_fichier_identique(tmp_path):
    local = b"contenu"
    s = source(tmp_path, b"contenu", hashlib.sha256(local).hexdigest())
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "x.bin").write_bytes(local)
    assert "non retéléchargé" not in tel.traiter(s, raw, verifier_seulement=False, forcer=True)
