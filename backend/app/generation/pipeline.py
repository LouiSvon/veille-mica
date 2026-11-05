"""Assistant : recherche, refus en deux couches, génération contrainte, vérification des citations et des nombres.

Garanties (testées avec un faux modèle) :
- le texte des citations vient toujours de la base, jamais du modèle ;
- une étiquette hors des passages envoyés est rejetée ;
- une réponse sans citation, tronquée ou dont les nombres ne se retrouvent pas dans les passages cités devient un refus (un refus peut reprendre les nombres de la question et des passages retrouvés) ;
- une panne du modèle ou de la recherche devient un refus de sécurité `echec_technique` ;
- chaque sortie porte l'avertissement « Ceci n'est pas un conseil juridique ».
"""
import json
import re
from dataclasses import dataclass

from pydantic import ValidationError

from app.generation.llm import LLM
from app.generation.prompt import construire_messages, etiquette_contraignant, reference
from app.generation.schema import CitationAffichee, ReponseAssistant, SortieModele, schema_json
from app.generation.verif import controle_nombres

MESSAGES_REFUS = {
    "hors_corpus": "Cette question ne porte pas sur un sujet couvert par les textes du corpus : je ne peux pas y répondre sans inventer.",
    "passages_insuffisants": "Les passages retrouvés ne permettent pas de répondre à cette question : je ne réponds pas plutôt que d'inventer.",
    "avis_juridique": "Je ne donne pas d'avis sur une situation particulière. Je peux seulement renvoyer aux textes qui énoncent la règle générale.",
    "echec_format": "Le modèle n'a pas produit de réponse exploitable : je préfère ne pas répondre.",
    "echec_verification": "La réponse produite n'a pas passé les contrôles du système (citation ou nombres non retrouvés dans les passages) : je ne la donne pas.",
    "echec_technique": "Le traitement a échoué techniquement (réponse tronquée ou contexte dépassé) : je ne réponds pas.",
}


@dataclass
class Config:
    k: int = 5
    mode: str = "dense"  # vectoriel seul : meilleur que l'hybride sur le dev (MRR 1,00 contre 0,93) puis sur le test (voir docs/choix-techniques.md)
    seuil_cosinus: float = 0.59  # règle v1 : docs/regles-notation.md ; valeur dérivée par eval/calibrer_seuil.py (v2 essayée puis abandonnée)
    essais: int = 2  # une seule relance si le JSON est invalide


RE_ETIQUETTE = re.compile(r"\bP(\d{1,2})\b")


def remplacer_etiquettes(texte: str, par_etiquette: dict[str, dict]) -> str:
    """Remplace « P3 » par la référence lisible du passage (« article 3, point 9 ») : le lecteur ne voit pas les étiquettes,
    et leurs chiffres ne sont pas des affirmations à contrôler. Une étiquette inconnue est laissée telle quelle."""
    def sub(m):
        p = par_etiquette.get(f"P{m.group(1)}")
        return reference(p) if p else m.group(0)
    return RE_ETIQUETTE.sub(sub, texte)


def _citation(etiquette: str, p: dict) -> CitationAffichee:
    return CitationAffichee(
        etiquette=etiquette, chunk_id=p["chunk_id"], source_titre=p["source_titre"], identifiant=p["identifiant"],
        reference=reference(p), texte=p["texte"], url=p["url"], version=p["version"],
        date_consultation=p["date_consultation"], contraignant=etiquette_contraignant(p.get("contraignant")),
    )


def _refus(motif: str, couche: str | None, diagnostic: dict, reponse: str | None = None, citations=None, nombres=None) -> ReponseAssistant:
    return ReponseAssistant(
        decision="refuser", motif=motif, couche_refus=couche, reponse=reponse or MESSAGES_REFUS[motif],
        citations=citations or [], controle_nombres=nombres or {}, diagnostic=diagnostic,
    )


def repondre(question: str, retriever, llm: LLM, config: Config | None = None) -> ReponseAssistant:
    cfg = config or Config()
    try:
        resultats, signaux = retriever.rechercher(question, k=cfg.k, mode=cfg.mode)
    except Exception as e:  # Ollama ou l'index indisponible : refus de sécurité, jamais une exception brute
        return _refus("echec_technique", "verification", {"erreur": f"recherche : {type(e).__name__}"})
    diag: dict = {"signaux": signaux, "seuil_cosinus": cfg.seuil_cosinus, "passages": [r["passage"]["chunk_id"] for r in resultats]}

    # Couche 1 : filtre sur le meilleur cosinus, sans appeler le modèle.
    cos = signaux.get("cosinus_top1")
    if cos is None or not resultats or cos < cfg.seuil_cosinus:
        return _refus("hors_corpus", "retrieval", diag)

    passages = [r["passage"] for r in resultats]
    messages, etiquettes = construire_messages(question, passages)
    schema = schema_json(etiquettes)
    sortie: SortieModele | None = None
    erreurs: list[str] = []
    for essai in range(1, cfg.essais + 1):
        try:
            res = llm.chat(messages, schema)
        except Exception as e:  # modèle indisponible, délai dépassé, réponse HTTP invalide
            diag["erreur"] = f"modèle : {type(e).__name__}"
            return _refus("echec_technique", "verification", diag)
        diag.update({"modele": res.modele, "prompt_eval_count": res.prompt_eval_count, "eval_count": res.eval_count,
                     "done_reason": res.done_reason, "num_ctx": res.num_ctx, "essais": essai})
        # Ollama ne signale pas une troncature du prompt : on la détecte par le décompte de tokens.
        if res.done_reason == "length" or res.prompt_eval_count >= res.num_ctx:
            diag["erreur"] = "troncature (réponse coupée ou prompt au-delà du contexte)"
            return _refus("echec_technique", "verification", diag)
        try:
            candidat = SortieModele.model_validate(json.loads(res.content))
            inconnues = [c for c in candidat.citations if c not in etiquettes]
            if inconnues:
                raise ValueError(f"étiquettes inconnues : {inconnues}")
            sortie = candidat
            break
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            erreurs.append(f"essai {essai} : {type(e).__name__}: {str(e)[:200]}")
    if sortie is None:
        diag["erreurs_format"] = erreurs
        return _refus("echec_format", "verification", diag)

    par_etiquette = dict(zip(etiquettes, passages))
    uniques = list(dict.fromkeys(sortie.citations))
    cites = [par_etiquette[e] for e in uniques]
    citations = [_citation(e, par_etiquette[e]) for e in uniques]
    # Une réponse ne peut s'appuyer que sur les passages qu'elle cite. Un refus ne cite souvent rien et peut décrire
    # les textes retrouvés (« l'ordonnance 2024-936 et MiCA ne traitent pas de... ») : ses nombres sont donc comparés à
    # tous les passages retrouvés. Une date tirée de la mémoire du modèle reste rejetée dans les deux cas.
    base_nombres = cites if sortie.decision == "repondre" else passages
    texte_reponse = remplacer_etiquettes(sortie.reponse, par_etiquette)
    # Les nombres de la question ne sont tolérés que pour un refus qui la reformule. Dans une réponse, un nombre repris de la
    # question (« jusqu'au 10 juillet 2027 ? ») ne doit pas être validé par la question elle-même.
    verif = controle_nombres(texte_reponse, base_nombres, question if sortie.decision == "refuser" else "")
    if not verif["ok"]:
        diag["reponse_rejetee"] = texte_reponse
        diag["motif_modele"] = sortie.motif
        return _refus("echec_verification", "verification", diag, citations=citations, nombres=verif)

    if sortie.decision == "repondre":
        return ReponseAssistant(decision="repondre", reponse=texte_reponse, citations=citations, controle_nombres=verif, diagnostic=diag)
    return _refus(sortie.motif, "modele", diag, reponse=texte_reponse.strip() or None, citations=citations, nombres=verif)
