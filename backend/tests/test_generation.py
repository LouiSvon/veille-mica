import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.generation.llm import ResultatLLM
from app.generation.pipeline import Config, repondre
from app.generation.prompt import CONSIGNES, construire_messages
from app.generation.schema import AVERTISSEMENT, SortieModele, schema_json
from app.generation.verif import controle_nombres, nombres

CHUNKS = Path(__file__).resolve().parents[2] / "data" / "processed" / "chunks.jsonl"


def passage(cid, texte, article="143", contraignant=True, **kw):
    base = {"chunk_id": cid, "texte": texte, "article": article, "paragraphe": "", "type": "article", "titre": "Mesures transitoires",
            "source": "mica", "source_titre": "Règlement (UE) 2023/1114 (MiCA)", "identifiant": "CELEX 32023R1114",
            "url": "https://exemple/mica", "version": "texte du JO", "date_consultation": "2026-11-05", "contraignant": contraignant}
    base.update(kw)
    return base


P143 = passage("mica-art-143", "3. Les prestataires peuvent continuer à le faire jusqu’au 1 er juillet 2026 ou jusqu’à ce qu’ils se voient octroyer un agrément.")
P1000 = passage("eba-par-81", "Un transfert s’élève à 1000 EUR ou excède ce montant.", article="paragraphe 81", type="paragraphe", contraignant=False, source_titre="Orientations EBA", identifiant="EBA/GL/2024/11")
PAMF = passage("amf-bloc-1", "Ces Orientations sont applicables à compter du 30 décembre 2024.", article="bloc 1", type="bloc", contraignant="a_fournir", source_titre="Position AMF", identifiant="DOC-2024-08")


class FauxRetriever:
    def __init__(self, passages, cosinus=0.8):
        self.passages, self.cosinus = passages, cosinus

    def rechercher(self, question, k=5, mode="hybride"):
        res = [{"passage": p, "rang": i, "score": 1.0, "mode": mode} for i, p in enumerate(self.passages[:k], start=1)]
        return res, {"cosinus_top1": self.cosinus, "bm25_top1": 5.0}


class FauxLLM:
    """Renvoie des sorties scriptées, une par appel. Garde les messages et schémas reçus."""
    def __init__(self, *sorties, done_reason="stop", prompt_eval_count=500, num_ctx=16384):
        self.sorties = list(sorties)
        self.done_reason, self.prompt_eval_count, self.num_ctx = done_reason, prompt_eval_count, num_ctx
        self.appels = []

    def chat(self, messages, schema):
        self.appels.append((messages, schema))
        s = self.sorties.pop(0) if len(self.sorties) > 1 else self.sorties[0]
        contenu = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False)
        return ResultatLLM(contenu, self.done_reason, self.prompt_eval_count, 40, self.num_ctx, "faux")


def rep(texte, cites=("P1",)):
    return {"decision": "repondre", "motif": None, "reponse": texte, "citations": list(cites)}


# --- chemin nominal ---

def test_reponse_nominale_texte_des_citations_vient_de_la_base():
    llm = FauxLLM(rep("Jusqu'au 1er juillet 2026, d'après l'article 143."))
    r = repondre("Jusqu'à quand ?", FauxRetriever([P143, P1000]), llm)
    assert r.decision == "repondre" and r.motif is None
    assert [c.chunk_id for c in r.citations] == ["mica-art-143"]
    assert r.citations[0].texte == P143["texte"]  # texte exact de la base
    assert r.citations[0].reference == "article 143" and r.citations[0].contraignant == "oui"
    assert r.controle_nombres["ok"] is True


def test_prompt_et_schema_envoient_les_memes_etiquettes_et_la_question_a_la_fin():
    llm = FauxLLM(rep("1er juillet 2026"))
    repondre("Ma question ?", FauxRetriever([P143, P1000, PAMF]), llm)
    messages, schema = llm.appels[0]
    assert schema["properties"]["citations"]["items"]["enum"] == ["P1", "P2", "P3"]
    assert messages[0]["content"] == CONSIGNES
    assert messages[1]["content"].rstrip().endswith("Question : Ma question ?")
    assert "[P1]" in messages[1]["content"] and P143["texte"] in messages[1]["content"]
    assert "contraignant : statut non vérifié" in messages[1]["content"]


# --- couche 1 ---

def test_couche_1_refuse_sans_appeler_le_modele():
    llm = FauxLLM(rep("x"))
    r = repondre("Capitale de la France ?", FauxRetriever([P143], cosinus=0.40), llm, Config(seuil_cosinus=0.59))
    assert r.decision == "refuser" and r.motif == "hors_corpus" and r.couche_refus == "retrieval"
    assert llm.appels == []


def test_couche_1_laisse_passer_au_dessus_du_seuil():
    llm = FauxLLM(rep("1er juillet 2026"))
    r = repondre("Q ?", FauxRetriever([P143], cosinus=0.60), llm, Config(seuil_cosinus=0.59))
    assert r.decision == "repondre" and len(llm.appels) == 1


# --- format et citations ---

def test_etiquette_inconnue_puis_valide_apres_une_relance():
    llm = FauxLLM(rep("1er juillet 2026", cites=("P9",)), rep("1er juillet 2026"))
    r = repondre("Q ?", FauxRetriever([P143]), llm)
    assert r.decision == "repondre" and r.diagnostic["essais"] == 2


def test_etiquette_inconnue_deux_fois_donne_echec_format():
    llm = FauxLLM(rep("1er juillet 2026", cites=("P9",)))
    r = repondre("Q ?", FauxRetriever([P143]), llm)
    assert r.decision == "refuser" and r.motif == "echec_format" and r.citations == []


def test_json_invalide_deux_fois_donne_echec_format():
    r = repondre("Q ?", FauxRetriever([P143]), FauxLLM("pas du json"))
    assert r.motif == "echec_format" and len(r.diagnostic["erreurs_format"]) == 2


def test_reponse_sans_citation_est_rejetee():
    r = repondre("Q ?", FauxRetriever([P143]), FauxLLM(rep("1er juillet 2026", cites=())))
    assert r.decision == "refuser" and r.motif == "echec_format"


def test_validation_du_schema_de_sortie():
    with pytest.raises(ValidationError):
        SortieModele(decision="repondre", motif="hors_corpus", reponse="x", citations=["P1"])
    with pytest.raises(ValidationError):
        SortieModele(decision="refuser", motif=None)
    assert SortieModele(decision="refuser", motif="avis_juridique", reponse="", citations=["P1"]).citations == ["P1"]


def test_schema_json_enumere_les_etiquettes():
    s = schema_json(["P1", "P2"])
    assert s["properties"]["citations"]["items"]["enum"] == ["P1", "P2"] and s["additionalProperties"] is False


# --- contrôle des nombres ---

def test_nombres_normalise_milliers_et_ordinal():
    assert nombres("1 000 EUR") == {"1000"} == nombres("1 000 EUR") == nombres("1000 EUR")
    assert nombres("1 000 000 EUR") == {"1000000"}
    assert nombres("jusqu’au 1 er juillet 2026") == {"1", "2026"}


def test_controle_nombres_accepte_les_nombres_des_passages_et_des_metadonnees():
    assert controle_nombres("Article 143 : jusqu'au 1er juillet 2026.", [P143])["ok"]
    assert controle_nombres("Le seuil est de 1 000 EUR.", [P1000])["ok"]  # « 1 000 » dans la réponse, « 1000 » dans le passage
    assert controle_nombres("Voir le paragraphe 81 des orientations.", [P1000])["ok"]  # numéro porté par les métadonnées


def test_controle_nombres_rejette_une_date_inventee():
    v = controle_nombres("Cela s'applique le 10 juillet 2027.", [P143])
    assert v["ok"] is False and "10" in v["inconnus"] and "2027" in v["inconnus"]


def test_pipeline_rejette_une_fuite_de_connaissance_type_q019():
    llm = FauxLLM(rep("L'AMLR s'applique à partir du 10 juillet 2027."))
    r = repondre("Date d'application de l'AMLR ?", FauxRetriever([P143]), llm)
    assert r.decision == "refuser" and r.motif == "echec_verification" and r.couche_refus == "verification"
    assert "2027" in r.controle_nombres["inconnus"] and "2027" in r.diagnostic["reponse_rejetee"]


def test_un_refus_peut_reprendre_les_nombres_de_la_question():
    """Cas q019 : le modèle refuse correctement en citant le numéro du règlement demandé. Ce n'est pas un nombre inventé."""
    sortie = {"decision": "refuser", "motif": "hors_corpus", "citations": [],
              "reponse": "Les passages ne contiennent aucune information sur le règlement (UE) 2024/1624."}
    r = repondre("Date d'application du règlement AMLR (UE) 2024/1624 ?", FauxRetriever([P143]), FauxLLM(sortie))
    assert r.decision == "refuser" and r.motif == "hors_corpus" and r.couche_refus == "modele"


def test_un_refus_qui_invente_un_nombre_est_rejete():
    sortie = {"decision": "refuser", "motif": "hors_corpus", "citations": [],
              "reponse": "Je ne l'ai pas, mais ce règlement s'applique le 10 juillet 2027."}
    r = repondre("Date d'application du règlement AMLR (UE) 2024/1624 ?", FauxRetriever([P143]), FauxLLM(sortie))
    assert r.motif == "echec_verification" and "2027" in r.controle_nombres["inconnus"]


def test_les_nombres_de_la_question_ne_blanchissent_pas_une_date_absente_de_la_question():
    v = controle_nombres("Réponse : 2027.", [P143], question="Que se passe-t-il en 2026 ?")
    assert v["ok"] is False and v["inconnus"] == ["2027"]


def test_un_refus_peut_decrire_les_textes_retrouves_meme_non_cites():
    """Cas q019 du second run : le refus nomme l'ordonnance 2024-936 et MiCA 2023/1114, présents dans les passages retrouvés."""
    sortie = {"decision": "refuser", "motif": "hors_corpus", "citations": [],
              "reponse": "Aucune information sur l'AMLR 2024/1624 ; les textes retrouvés sont la décision 2023/1114 et le point 143."}
    r = repondre("Date de l'AMLR 2024/1624 ?", FauxRetriever([P143]), FauxLLM(sortie))
    assert r.decision == "refuser" and r.motif == "hors_corpus" and r.couche_refus == "modele"


def test_un_refus_ne_peut_pas_blanchir_une_date_hors_passages():
    sortie = {"decision": "refuser", "motif": "hors_corpus", "citations": [],
              "reponse": "Je n'ai pas le texte, mais la date est le 10 juillet 2027, et l'article 143 existe."}
    r = repondre("Date de l'AMLR ?", FauxRetriever([P143]), FauxLLM(sortie))
    assert r.motif == "echec_verification" and "2027" in r.controle_nombres["inconnus"]


def test_une_reponse_reste_limitee_aux_passages_cites():
    """La tolérance des refus ne s'étend pas aux réponses : un nombre d'un passage retrouvé mais non cité est rejeté."""
    r = repondre("Q ?", FauxRetriever([P143, P1000]), FauxLLM(rep("Le seuil est de 1000 EUR.", cites=("P1",))))
    assert r.motif == "echec_verification"


def test_les_etiquettes_sont_remplacees_par_la_reference_lisible():
    r = repondre("Q ?", FauxRetriever([P143, P1000]), FauxLLM(rep("Voir (P1) : jusqu'au 1er juillet 2026.", cites=("P1",))))
    assert r.decision == "repondre" and "P1" not in r.reponse and "(article 143)" in r.reponse


def test_une_etiquette_dans_un_refus_ne_declenche_pas_de_faux_nombre_inconnu():
    """Cas q043 : le refus écrit « (P5) » ; le 5 de l'étiquette n'est pas une affirmation."""
    sortie = {"decision": "refuser", "motif": "avis_juridique", "citations": ["P1"],
              "reponse": "Voir (P1) et (P2) : règle générale seulement, sans qualifier votre projet."}
    r = repondre("Mon projet est-il conforme ?", FauxRetriever([P143, P1000]), FauxLLM(sortie))
    assert r.motif == "avis_juridique" and r.couche_refus == "modele" and "P2" not in r.reponse


def test_une_etiquette_inconnue_est_laissee_telle_quelle_et_son_nombre_reste_controle():
    from app.generation.pipeline import remplacer_etiquettes
    assert remplacer_etiquettes("voir P9", {"P1": P143}) == "voir P9"


def test_les_nombres_d_un_passage_non_cite_ne_comptent_pas():
    llm = FauxLLM(rep("Le seuil est de 1000 EUR.", cites=("P1",)))  # P1 = P143 qui ne contient pas 1000
    r = repondre("Q ?", FauxRetriever([P143, P1000]), llm)
    assert r.motif == "echec_verification"


# --- avis juridique ---

def test_avis_juridique_peut_citer_les_articles_sans_conclure():
    sortie = {"decision": "refuser", "motif": "avis_juridique", "reponse": "", "citations": ["P1"]}
    r = repondre("Puis-je continuer sans agrément ?", FauxRetriever([P143]), FauxLLM(sortie))
    assert r.decision == "refuser" and r.motif == "avis_juridique" and r.couche_refus == "modele"
    assert r.citations[0].texte == P143["texte"]
    assert r.reponse  # message par défaut quand le modèle ne dit rien


# --- troncature ---

def test_reponse_tronquee_est_un_echec_technique():
    r = repondre("Q ?", FauxRetriever([P143]), FauxLLM(rep("1er juillet 2026"), done_reason="length"))
    assert r.decision == "refuser" and r.motif == "echec_technique"


def test_prompt_au_niveau_du_contexte_est_un_echec_technique():
    r = repondre("Q ?", FauxRetriever([P143]), FauxLLM(rep("1er juillet 2026"), prompt_eval_count=16384, num_ctx=16384))
    assert r.motif == "echec_technique"
    ok = repondre("Q ?", FauxRetriever([P143]), FauxLLM(rep("1er juillet 2026"), prompt_eval_count=16383, num_ctx=16384))
    assert ok.decision == "repondre"


# --- sorties ---

def test_avertissement_dans_toutes_les_branches():
    cas = [
        repondre("Q ?", FauxRetriever([P143]), FauxLLM(rep("1er juillet 2026"))),
        repondre("Q ?", FauxRetriever([P143], cosinus=0.1), FauxLLM(rep("x"))),
        repondre("Q ?", FauxRetriever([P143]), FauxLLM("pas du json")),
        repondre("Q ?", FauxRetriever([P143]), FauxLLM(rep("le 10 juillet 2027"))),
        repondre("Q ?", FauxRetriever([P143]), FauxLLM(rep("x"), done_reason="length")),
        repondre("Q ?", FauxRetriever([P143]), FauxLLM({"decision": "refuser", "motif": "hors_corpus", "reponse": "", "citations": []})),
    ]
    assert len(cas) == 6
    for r in cas:
        assert r.avertissement == AVERTISSEMENT == "Ceci n'est pas un conseil juridique."
        assert json.loads(r.model_dump_json())["avertissement"] == AVERTISSEMENT


def test_statut_non_verifie_n_est_jamais_affiche_comme_oui_ou_non():
    llm = FauxLLM(rep("applicables à compter du 30 décembre 2024", cites=("P1",)))
    r = repondre("Q ?", FauxRetriever([PAMF]), llm)
    assert r.citations[0].contraignant == "statut non vérifié"


# --- taille du prompt dans le pire cas réel ---

@pytest.mark.skipif(not CHUNKS.exists(), reason="passages absents")
def test_le_pire_prompt_reel_tient_dans_le_contexte():
    """Cinq plus gros passages du corpus : estimation prudente à 2,5 caractères par token, marge de 20 %."""
    passages = [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines()]
    cinq = sorted(passages, key=lambda p: -len(p["texte"]))[:5]
    messages, _ = construire_messages("Question ?", cinq)
    chars = sum(len(m["content"]) for m in messages)
    assert chars / 2.5 < 16384 * 0.8, f"{chars} caractères : risque de dépasser le contexte"


# --- défauts relevés à la relecture indépendante ---

def test_un_nombre_faux_repris_de_la_question_ne_valide_pas_une_reponse():
    """Injection par la question : « jusqu'au 10 juillet 2027 ? » ne doit pas faire accepter « Oui, jusqu'au 10 juillet 2027 »."""
    r = repondre("Les prestataires peuvent-ils continuer jusqu'au 10 juillet 2027 ?", FauxRetriever([P143]),
                 FauxLLM(rep("Oui, jusqu'au 10 juillet 2027.")))
    assert r.decision == "refuser" and r.motif == "echec_verification" and "2027" in r.controle_nombres["inconnus"]


def test_une_panne_du_modele_devient_un_refus_de_securite():
    class LLMEnPanne:
        def chat(self, messages, schema):
            raise ConnectionError("Ollama injoignable")
    r = repondre("Q ?", FauxRetriever([P143]), LLMEnPanne())
    assert r.decision == "refuser" and r.motif == "echec_technique" and r.avertissement == AVERTISSEMENT
    assert "Ollama" not in r.reponse


def test_une_panne_de_la_recherche_devient_un_refus_de_securite():
    class RetrieverEnPanne:
        def rechercher(self, question, k=5, mode="hybride"):
            raise ConnectionError("bge-m3 injoignable")
    r = repondre("Q ?", RetrieverEnPanne(), FauxLLM(rep("x")))
    assert r.motif == "echec_technique" and r.couche_refus == "verification" and r.avertissement == AVERTISSEMENT
