"""Contrôle du jeu de questions : schéma, extraits de référence mot pour mot, découpage dev/test."""
import json
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[2]
QUESTIONS = RACINE / "eval" / "questions.jsonl"
CHUNKS = RACINE / "data" / "processed" / "chunks.jsonl"

SPLITS = {"dev", "test"}
STATUTS = {"repondable", "hors_corpus", "piege"}
VALIDATIONS = {"propose_non_valide", "valide", "corrige", "refuse"}
CATEGORIES = {"fait_direct", "definition", "date_applicabilite", "croisement", "hors_corpus", "piege"}
CHAMPS = {"id", "split", "categorie", "question", "reponse_attendue", "statut", "passages_reference",
          "comportement_attendu", "auteur", "validation", "notes"}


def charger():
    return [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_schema_et_valeurs_autorisees():
    qs = charger()
    assert qs, "fichier vide"
    for q in qs:
        assert CHAMPS <= set(q), f"{q.get('id')}: champs manquants {CHAMPS - set(q)}"
        assert q["split"] in SPLITS and q["statut"] in STATUTS and q["validation"] in VALIDATIONS
        assert q["categorie"] in CATEGORIES
        assert q["question"].strip().endswith(("?", ".")) and q["auteur"] in {"assistant", "louis"}
    assert len({q["id"] for q in qs}) == len(qs)
    assert len({q["question"] for q in qs}) == len(qs), "question en double"


def test_regles_selon_le_statut():
    for q in charger():
        if q["statut"] == "repondable":
            assert q["reponse_attendue"].strip() and q["passages_reference"], q["id"]
        else:
            assert q["reponse_attendue"] == "" and q["comportement_attendu"].strip(), q["id"]
        if q["statut"] == "hors_corpus":
            assert q["passages_reference"] == [], q["id"]


def charger_passages():
    passages = {}
    for l in CHUNKS.read_text(encoding="utf-8").splitlines():
        c = json.loads(l)
        passages[c["chunk_id"]] = c["texte"]
    return passages


def problemes_de_reference(questions, passages):
    """Liste les références inconnues ou dont un extrait n'est pas mot pour mot dans le passage."""
    problemes = []
    for q in questions:
        for r in q["passages_reference"]:
            if r["chunk_id"] not in passages:
                problemes.append((q["id"], "passage inconnu", r["chunk_id"]))
                continue
            if not r["extraits"]:
                problemes.append((q["id"], "aucun extrait", r["chunk_id"]))
            for e in r["extraits"]:
                if e not in passages[r["chunk_id"]]:
                    problemes.append((q["id"], "extrait absent", r["chunk_id"]))
    return problemes


@pytest.mark.skipif(not CHUNKS.exists(), reason="passages absents (data/processed non versionné)")
def test_extraits_de_reference_sont_mot_pour_mot_dans_les_passages():
    assert problemes_de_reference(charger(), charger_passages()) == []


@pytest.mark.skipif(not CHUNKS.exists(), reason="passages absents (data/processed non versionné)")
def test_le_controle_detecte_un_extrait_modifie_et_un_passage_inconnu():
    """Cas négatifs : un extrait changé d'un mot, puis un identifiant de passage inexistant."""
    passages = charger_passages()
    q = next(x for x in charger() if x["id"] == "q007")
    q["passages_reference"][0]["extraits"][0] = q["passages_reference"][0]["extraits"][0].replace("30 décembre", "31 décembre")
    assert ("q007", "extrait absent", "mica-art-149") in problemes_de_reference([q], passages)
    q["passages_reference"][0]["chunk_id"] = "mica-art-999"
    assert ("q007", "passage inconnu", "mica-art-999") in problemes_de_reference([q], passages)


def test_repartition_dev_test():
    qs = charger()
    assert sum(q["split"] == "dev" for q in qs) >= 10, "il faut au moins 10 questions de développement"
    assert sum(q["split"] == "test" for q in qs) >= 1
