import json
import urllib.request
from pathlib import Path

import numpy as np
import pytest

from app.retrieval.bm25 import BM25, tokeniser
from app.retrieval.dense import embedder_ollama, construire_index, normaliser
from app.retrieval.retriever import Retriever, fusion_rrf, texte_indexe

CHUNKS = Path(__file__).resolve().parents[2] / "data" / "processed" / "chunks.jsonl"


def passage(pid, texte, article="1", source="Règlement test", titre="", type_="article", paragraphe=""):
    return {"chunk_id": pid, "texte": texte, "article": article, "source_titre": source, "titre": titre,
            "type": type_, "paragraphe": paragraphe}


CORPUS = [
    passage("a", "Les prestataires de services sur crypto-actifs peuvent continuer jusqu'au 1er juillet 2026.", "143", titre="Mesures transitoires"),
    passage("b", "Un livre blanc est rédigé, notifié et publié par l'offreur.", "6", titre="Contenu du livre blanc"),
    passage("c", "Les transferts de fonds sont accompagnés d'informations sur le donneur d'ordre.", "4", source="Règlement 2023/1113"),
    passage("d", "Définitions : on entend par crypto-actif une représentation numérique.", "3", titre="Définitions"),
]


def faux_embedder(appels=None):
    """Embedder de test : sac de mots hachés. Deux textes qui partagent des mots ont un cosinus élevé."""
    def embed(textes):
        if appels is not None:
            appels.append(list(textes))
        m = np.zeros((len(textes), 64), dtype=np.float32)
        for i, t in enumerate(textes):
            for mot in tokeniser(t):
                m[i, hash_stable(mot) % 64] += 1.0
        return normaliser(m)
    return embed


def hash_stable(mot):
    return sum((j + 1) * ord(c) for j, c in enumerate(mot))


# --- tokenisation ---

def test_tokeniser_accents_pluriels_references_et_mots_vides():
    t = tokeniser("Les prestataires de l’article 143 du règlement 2023/1113")
    assert "prestataire" in t and "reglement" in t and "143" in t
    assert "2023/1113" in t and "2023" in t
    assert "les" not in t and "de" not in t and "du" not in t


# --- BM25 ---

def test_bm25_classe_le_bon_passage_premier():
    b = BM25([texte_indexe(p) for p in CORPUS])
    assert b.classer("livre blanc", 3)[0][0] == 1
    assert b.classer("donneur d'ordre transferts", 3)[0][0] == 2


def test_bm25_retrouve_un_numero_d_article():
    b = BM25([texte_indexe(p) for p in CORPUS])
    assert b.classer("article 143", 1)[0][0] == 0


def test_bm25_terme_inconnu_ne_renvoie_rien():
    b = BM25([texte_indexe(p) for p in CORPUS])
    assert b.classer("xyzzy", 3) == []


# --- fusion RRF ---

def test_rrf_un_passage_bien_classe_deux_fois_bat_un_premier_unique():
    f = dict(fusion_rrf([[1, 2, 3], [9, 2, 4]]))
    assert f[2] > f[1] and f[2] > f[9]
    assert [i for i, _ in fusion_rrf([[1, 2, 3], [9, 2, 4]])][0] == 2


def test_rrf_est_deterministe_a_egalite():
    assert fusion_rrf([[1], [2]]) == fusion_rrf([[1], [2]])
    assert [i for i, _ in fusion_rrf([[1], [2]])] == [1, 2]


# --- Retriever ---

def test_retriever_trois_modes():
    r = Retriever(CORPUS, embedder=faux_embedder())
    for mode in ("bm25", "dense", "hybride"):
        res = r.chercher("livre blanc notifié publié", k=2, mode=mode)
        assert res[0]["passage"]["chunk_id"] == "b", mode
        assert [x["rang"] for x in res] == [1, 2][: len(res)]


def test_retriever_sans_embedder_refuse_le_mode_dense():
    r = Retriever(CORPUS)
    assert r.chercher("livre blanc", mode="bm25")[0]["passage"]["chunk_id"] == "b"
    with pytest.raises(RuntimeError):
        r.chercher("livre blanc", mode="dense")


# --- cache d'embeddings ---

def test_cache_ne_recalcule_que_les_textes_modifies(tmp_path):
    cache = tmp_path / "emb.npz"
    textes = ["alpha beta", "gamma delta", "epsilon"]
    appels = []
    construire_index(textes, faux_embedder(appels), cache, "m")
    assert sum(len(a) for a in appels) == 3
    appels.clear()
    construire_index(textes, faux_embedder(appels), cache, "m")
    assert appels == []  # tout vient du cache
    construire_index(["alpha beta", "gamma MODIFIE", "epsilon"], faux_embedder(appels), cache, "m")
    assert sum(len(a) for a in appels) == 1 and appels[0] == ["gamma MODIFIE"]


def test_cache_distingue_deux_modeles(tmp_path):
    cache = tmp_path / "emb.npz"
    appels = []
    construire_index(["alpha"], faux_embedder(appels), cache, "modele-1")
    construire_index(["alpha"], faux_embedder(appels), cache, "modele-2")
    assert len(appels) == 2


# --- intégration réelle (Ollama + bge-m3) ---

def ollama_pret():
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            return any(m["name"].startswith("bge-m3") for m in json.load(r)["models"])
    except Exception:
        return False


@pytest.mark.skipif(not ollama_pret(), reason="Ollama ou bge-m3 indisponible")
def test_bge_m3_pertinent_au_dessus_du_hors_sujet():
    v = embedder_ollama()([
        "Quelle est la date d'application des orientations de l'ABE ?",
        "Les présentes orientations s’appliquent à compter du 30 décembre 2024.",
        "Recette de la tarte aux pommes avec de la cannelle.",
    ])
    assert v.shape == (3, 1024)
    assert float(v[0] @ v[1]) > float(v[0] @ v[2]) + 0.1


@pytest.mark.skipif(not (ollama_pret() and CHUNKS.exists()), reason="Ollama ou passages indisponibles")
def test_corpus_reel_la_question_sur_la_transition_trouve_l_article_143(tmp_path):
    r = Retriever.depuis_fichier(CHUNKS, embedder=embedder_ollama(), cache=tmp_path / "emb.npz", nom_modele="bge-m3")
    ids = [x["passage"]["chunk_id"] for x in r.chercher(
        "Jusqu'à quand les prestataires déjà actifs peuvent-ils continuer sans agrément MiCA ?", k=5, mode="hybride")]
    assert any(i.startswith("mica-art-143") for i in ids), ids
