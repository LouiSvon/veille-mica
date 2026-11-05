import json

from fastapi.testclient import TestClient

from app.api import main as api_main
from app.api.main import creer_app
from app.generation.schema import AVERTISSEMENT
from tests.test_generation import P143, FauxLLM, FauxRetriever, rep


def client(llm=None, retriever=None):
    return TestClient(creer_app(retriever or FauxRetriever([P143]), llm or FauxLLM(rep("Jusqu'au 1er juillet 2026."))))


def test_sante_decrit_le_corpus_et_porte_l_avertissement():
    with client() as c:
        r = c.get("/health")
    corps = r.json()
    assert r.status_code == 200 and corps["statut"] == "ok" and corps["avertissement"] == AVERTISSEMENT
    assert corps["nombre_passages"] == 1 and corps["sources"][0]["source"] == "mica"


def test_ask_repond_avec_citation_et_avertissement():
    with client() as c:
        r = c.post("/ask", json={"question": "Jusqu'à quand ?"})
    corps = r.json()
    assert r.status_code == 200 and corps["decision"] == "repondre"
    assert corps["avertissement"] == AVERTISSEMENT == "Ceci n'est pas un conseil juridique."
    assert corps["citations"][0]["texte"] == P143["texte"] and corps["citations"][0]["url"] == P143["url"]


def test_ask_refus_porte_aussi_l_avertissement():
    with client(retriever=FauxRetriever([P143], cosinus=0.1)) as c:
        corps = c.post("/ask", json={"question": "Capitale de la France ?"}).json()
    assert corps["decision"] == "refuser" and corps["couche_refus"] == "retrieval" and corps["avertissement"] == AVERTISSEMENT


def test_ask_valide_l_entree():
    with client() as c:
        assert c.post("/ask", json={"question": ""}).status_code == 422
        assert c.post("/ask", json={"question": "ab"}).status_code == 422
        assert c.post("/ask", json={"question": "x" * 1001}).status_code == 422
        assert c.post("/ask", json={}).status_code == 422
        assert c.post("/ask", json={"question": "x" * 1000}).status_code == 200


def test_cors_limite_aux_origines_locales():
    with client() as c:
        ok = c.options("/ask", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
        autre = c.options("/ask", headers={"Origin": "https://exemple.org", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in autre.headers


def test_une_erreur_du_modele_ne_fuit_pas_en_reponse_inventee():
    with client(llm=FauxLLM("pas du json")) as c:
        corps = c.post("/ask", json={"question": "Q ?"}).json()
    assert corps["decision"] == "refuser" and corps["motif"] == "echec_format" and corps["citations"] == []
    assert json.loads(json.dumps(corps))["avertissement"] == AVERTISSEMENT


def test_entree_invalide_renvoie_un_json_avec_avertissement():
    with client() as c:
        r = c.post("/ask", json={"question": "ab"})
    assert r.status_code == 422 and r.json()["avertissement"] == AVERTISSEMENT


def test_question_faite_d_espaces_est_refusee_avant_toute_recherche():
    llm = FauxLLM(rep("x"))
    with client(llm=llm) as c:
        assert c.post("/ask", json={"question": "     "}).status_code == 422
        assert c.post("/ask", json={"question": "  ab  "}).status_code == 422
    assert llm.appels == []


def test_erreur_interne_renvoie_un_500_json_avec_avertissement_sans_detail(monkeypatch):
    def boum(*a, **k):
        raise RuntimeError("secret interne /chemin/prive")
    monkeypatch.setattr(api_main, "repondre", boum)
    with TestClient(creer_app(FauxRetriever([P143]), FauxLLM(rep("x"))), raise_server_exceptions=False) as c:
        r = c.post("/ask", json={"question": "Question valide ?"})
    assert r.status_code == 500 and r.json()["avertissement"] == AVERTISSEMENT
    assert "secret" not in r.text and "chemin" not in r.text


def test_le_texte_non_verifie_du_modele_n_est_pas_renvoye_au_client():
    with client(llm=FauxLLM(rep("La date est le 10 juillet 2027."))) as c:
        corps = c.post("/ask", json={"question": "Une question ?"}).json()
    assert corps["motif"] == "echec_verification"
    assert "reponse_rejetee" not in corps["diagnostic"] and "2027" not in json.dumps(corps["diagnostic"])
    assert "2027" in corps["controle_nombres"]["inconnus"]
