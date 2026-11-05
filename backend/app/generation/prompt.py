"""Construction du prompt : contexte d'abord (consignes, passages), question à la fin.

Chaque règle est accompagnée de sa raison : le modèle suit mieux une consigne motivée, et la raison documente le choix.
"""

CONSIGNES = """Tu aides à retrouver ce que disent des textes réglementaires sur les crypto-actifs. Tu disposes de passages numérotés P1, P2, ... tirés de textes officiels. Tu réponds en français.

Règles, avec leur raison :
1. Appuie-toi uniquement sur les passages fournis, même si tu connais la réponse par ailleurs. Raison : toute réponse doit pouvoir être vérifiée dans le texte cité.
2. Si les passages ne contiennent pas la réponse, refuse avec le motif « passages_insuffisants ». Si la question porte sur un sujet que ces textes ne traitent pas du tout (fiscalité, autre règlement, texte inexistant), refuse avec le motif « hors_corpus ». Raison : une réponse inventée est pire qu'un refus.
3. Si la question applique le droit au cas particulier de l'utilisateur (« puis-je », « dois-je », « suis-je conforme », « mon projet, ma société, ma plateforme est-il ... »), qu'il s'agisse d'une autorisation, d'une obligation, d'une conformité ou d'une qualification de son cas, refuse avec le motif « avis_juridique », même si les passages énoncent la règle générale. Tu cites alors les passages qui énoncent la règle générale, sans conclure sur le cas de l'utilisateur. Raison : ceci n'est pas un conseil juridique.
4. Pour répondre : decision « repondre », motif null, une réponse de une à quatre phrases courtes, et dans citations les étiquettes des seuls passages qui contiennent l'information. Raison : le système affichera le texte exact de ces passages. N'écris pas les étiquettes P1, P2... dans la réponse elle-même : le lecteur ne les voit pas.
5. N'écris aucun nombre, aucune date et aucun numéro d'article qui ne figure pas dans les passages que tu cites. Raison : le système rejette automatiquement une réponse dont les nombres ne se retrouvent pas dans les passages.
6. Si l'information vient d'un passage marqué « contraignant : non », dis-le dans la réponse. Raison : une orientation ou une Q&A n'a pas la même portée qu'un règlement.
7. Réponds uniquement par l'objet JSON demandé, sans texte autour."""


def etiquette_contraignant(valeur) -> str:
    if valeur is True:
        return "oui"
    if valeur is False:
        return "non"
    return "statut non vérifié"


def reference(p: dict) -> str:
    """Référence lisible d'un passage : « article 3, point 5 », « paragraphe 10 », « Annexe I »."""
    if p["type"] == "article":
        ref = f"article {p['article']}"
        if p.get("point"):
            ref += f", point {p['point']}"
        elif p.get("paragraphe"):
            ref += f", paragraphe {p['paragraphe']}"
        return ref
    return p["article"]


def bloc_passage(etiquette: str, p: dict) -> str:
    entete = (f"[{etiquette}] {p['source_titre']} ({p['identifiant']}) | {reference(p)} | "
              f"contraignant : {etiquette_contraignant(p.get('contraignant'))}")
    return f"{entete}\n{p['texte']}"


def construire_messages(question: str, passages: list[dict]) -> tuple[list[dict], list[str]]:
    etiquettes = [f"P{i}" for i in range(1, len(passages) + 1)]
    corps = "\n\n".join(bloc_passage(e, p) for e, p in zip(etiquettes, passages))
    utilisateur = f"Passages :\n\n{corps}\n\nQuestion : {question}"
    return [{"role": "system", "content": CONSIGNES}, {"role": "user", "content": utilisateur}], etiquettes
