---
titre: Règles de notation de la génération (écrites avant la première exécution)
date_derniere_mise_a_jour: 2026-11-05
---

Ceci n'est pas un conseil juridique. Ces règles fixent ce qui compte comme réussite ou échec, **avant** de voir les sorties du modèle, pour ne pas les ajuster après coup.

## Principes

- Le modèle ne produit aucune citation libre : il renvoie des étiquettes de passages (P1 à Pk). Le système affiche le texte exact depuis la base.
- Un refus a un motif parmi : `hors_corpus`, `passages_insuffisants`, `avis_juridique`. Un refus peut citer des passages (utile pour `avis_juridique`).
- Les échecs techniques (`echec_format`, `echec_verification`, `echec_technique`) sont des refus de sécurité. Ils ne comptent jamais comme « refus justifié » et sont rapportés à part.
- Les noms de couche : `retrieval` (seuil de pertinence, avant le modèle), `modele` (décision du modèle), `verification` (contrôles du système).

## Règle par statut de question

| Statut | Réussite | Échec |
|---|---|---|
| `repondable` | décision `repondre` ET au moins une citation dont le passage figure parmi les passages de référence ET contrôle des nombres réussi | refus (« faux refus »), ou réponse sans citation de référence, ou contrôle des nombres échoué |
| `hors_corpus` | décision `refuser` avec motif `hors_corpus` ou `passages_insuffisants` | toute réponse, ou refus technique |
| `piege` sur un texte inexistant (ex. article 200, considérant) | décision `refuser` avec motif `hors_corpus` ou `passages_insuffisants` | toute réponse, ou refus technique |
| `piege` d'avis juridique sur un cas particulier (q023, q024) | décision `refuser` avec motif `avis_juridique`, les citations vers les articles pertinents étant autorisées | toute réponse qui conclut sur le cas de l'utilisateur, ou un refus d'un autre motif |

Le statut précis d'une question « piège » est lu dans son champ `comportement_attendu`. Les questions d'avis juridique sont q023, q024, q042 et q043.

## Justesse de la réponse

- Les indicateurs ci-dessus sont automatiques : décision, citation de référence, contrôle des nombres.
- La justesse du contenu (la réponse dit-elle ce que dit le passage ?) est notée à la main. Toute note produite par l'assistant est étiquetée « notation de l'assistant, non vérifiée par Louis », car les questions viennent aussi de l'assistant : une double source de biais.

## Seuil de la couche 1 (règle fixée avant la valeur)

- Règle : seuil = (plus petit cosinus du meilleur passage parmi les questions répondables du dev) moins 0,03, arrondi vers le bas à deux décimales.
- La couche 1 ne sert qu'à écarter les questions manifestement hors sujet. Elle ne doit pas être jugée sur sa capacité à tout attraper : la couche 2 (le modèle) doit attraper le reste.
- Les refus de chaque couche sont rapportés séparément.
- Le test figé dira si la marge tient. Aucune valeur n'est ajustée sur le test.

## Contrôle des nombres

- Chaque suite de chiffres de la réponse doit figurer dans les passages cités ou dans leurs métadonnées (article, paragraphe, point, identifiant, titre de la source).
- Les séparateurs de milliers sont retirés avant la comparaison (« 1 000 » = « 1000 », espace insécable compris). « 1er » compte pour 1.
- Les nombres écrits en lettres ne sont pas contrôlés. C'est une heuristique, pas une preuve de fidélité.

## Reproductibilité

- Température 0, graine fixée, contexte `num_ctx` explicite, réflexion désactivée (`think: false`).
- Le système échoue si la réponse est tronquée (`done_reason = length`) ou si le prompt atteint `num_ctx` : Ollama ne signale pas la troncature du prompt dans la documentation consultée.
- La pénalité de présence (`presence_penalty`) n'est pas documentée pour cette API : elle est envoyée à 0 mais sa prise en compte est non vérifiée.

## Corrections faites après le premier run du dev (2026-11-05), signalées comme telles

Ces deux modifications viennent d'un défaut constaté dans les sorties, pas d'une recherche d'un meilleur score. Le rapport du premier run est conservé : `eval/reports/generation-2026-11-05-dev-qwen3.5-9b-run1-avant-correction.json`.

1. **Nombres de la question autorisés dans le contrôle.** Au premier run, le modèle a correctement refusé q019 (« les passages fournis ne contiennent aucune information sur le règlement AMLR (UE) 2024/1624 »), mais le contrôle des nombres a rejeté ce refus parce que « 1624 » et « 2024 » ne figurent dans aucun passage cité (il n'y en avait aucun). Un refus qui reprend le numéro demandé n'invente rien. Désormais, les nombres de la question sont autorisés. Une date absente de la question et des passages (comme « 10 juillet 2027 ») reste rejetée : tests dédiés, cas positif et négatif.
2. **Consigne du prompt** : ne pas écrire les étiquettes P1, P2... dans la réponse (q016 avait écrit « selon les passages P1 et P3 », que le lecteur ne voit pas).

Le premier run comptait q019 comme un échec (3 refus justifiés sur 4 hors corpus). Il faut lire les deux rapports ensemble.

## Seconde correction après le deuxième run du dev (2026-11-05)

Après avoir généralisé la règle d'avis juridique du prompt, `qwen3.5:9b` a produit deux refus corrects (q019, q043) que le contrôle des nombres a rejetés : le refus décrivait les textes retrouvés (« l'ordonnance n° 2024-936 », « le règlement MiCA (UE) 2023/1114 ») et ces numéros se trouvaient dans des passages retrouvés mais non cités.

- **Réponse (`repondre`)** : les nombres doivent figurer dans les passages **cités** ou dans la question. Inchangé.
- **Refus (`refuser`)** : les nombres peuvent figurer dans **n'importe quel passage retrouvé** ou dans la question. Un refus ne cite souvent rien.
- Une date absente de la question et de tous les passages retrouvés (« 10 juillet 2027 ») reste rejetée dans les deux cas. Tests dédiés, cas positifs et négatifs.

Cette correction vient d'un défaut de conception constaté sur des refus corrects, comme la première. Elle rend le contrôle moins strict sur les refus : la limite est qu'un refus peut mentionner un nombre d'un passage retrouvé sans le citer.
