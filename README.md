---
titre: veille-mica, assistant de veille réglementaire sur les crypto-actifs
date_derniere_mise_a_jour: 2026-11-05
---

> **Ceci n'est pas un conseil juridique.** Cet outil retrouve des passages de textes officiels et les cite. Il ne qualifie aucune situation particulière, ne dit pas si une activité est conforme et ne remplace ni un avocat ni l'autorité compétente. Le droit évolue : vérifiez toujours la version et la date de chaque source citée.

# veille-mica

Assistant de recherche (RAG) qui répond en français à des questions sur la réglementation européenne et française des crypto-actifs (MiCA et textes liés). Chaque réponse affiche **le texte exact du passage officiel utilisé**, avec sa version, sa date de consultation et un lien vers la source. Si les textes du corpus ne permettent pas de répondre, l'assistant **refuse et dit pourquoi** au lieu d'inventer.

Projet personnel d'apprentissage : construire un cas d'usage d'IA générative avec une évaluation mesurée, ses limites comprises. 100 % local (Ollama), aucune API payante, pas de démo en ligne. Développé avec l'aide de l'assistant IA Claude (Anthropic) : voir « Lecture honnête ».

## Ce que ça donne

Question : « Quelles orientations antérieures les orientations de l'ABE sur la travel rule abrogent-elles, et à quelle date ? »

Réponse : les orientations communes prises en application de l'article 25 du règlement (UE) 2015/847 sont abrogées avec effet au 30 décembre 2024. Citation affichée : « paragraphe 11 », EBA/GL/2024/11, non contraignant, avec le texte du paragraphe et le lien de la source.

Question hors corpus : « Quel est le taux d'imposition des plus-values sur crypto-actifs en France ? » Refus : le sujet n'est pas couvert par les textes du corpus.

## Démarrage rapide

Prérequis : [uv](https://docs.astral.sh/uv/), Node 20.9 ou plus, [Ollama](https://ollama.com), poppler (`pdftotext`, par exemple `brew install poppler`). Testé sous macOS avec Ollama 0.35 et 24 Go de mémoire.

```bash
make setup        # dépendances Python et Node
make modeles      # télécharge bge-m3 et qwen3.5:9b (environ 7,8 Go) : à lancer en connaissance de cause
make telecharger  # textes EUR-Lex, EBA, AMF (voir « Sources manuelles » ci-dessous)
make ingest       # découpe en passages
make serve        # API sur http://localhost:8000
make front        # interface sur http://localhost:3000
```

Sources manuelles : Légifrance refuse les téléchargements par script (HTTP 403). Ouvrez la page de l'ordonnance, imprimez-la en PDF et déposez le fichier sous `data/raw/ordonnance-2024-936-fr.pdf`. Le hash du registre est celui de l'impression d'origine : une autre impression donnera un autre hash, et `make ingest` s'arrêtera tant que vous ne mettez pas le registre à jour.

## Sources

Uniquement des textes officiels et publics. Registre complet : [data/sources.yaml](data/sources.yaml) (URL, version, date de consultation, hash). Les textes bruts ne sont pas versionnés.

| Texte | Version utilisée | Consulté le | Passages |
|---|---|---|---|
| [Règlement (UE) 2023/1114 (MiCA)](https://eur-lex.europa.eu/eli/reg/2023/1114/oj/fra) | texte du Journal officiel, non consolidé | 2026-11-05 | 597 |
| [Règlement (UE) 2023/1113 (transferts de fonds et de crypto-actifs)](https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32023R1113) | texte du Journal officiel, non consolidé | 2026-11-05 | 94 |
| [EBA/GL/2024/11 (orientations « travel rule »)](https://www.eba.europa.eu/activities/single-rulebook/regulatory-activities/anti-money-laundering-and-countering-financing-terrorism/guidelines-information-requirements-relation-transfers-funds-and-certain-crypto-assets-transfers) | version française corrigée du 4 juillet 2024 | 2026-11-05 | 101 |
| [Position AMF DOC-2024-08](https://www.amf-france.org/fr/reglementation/doctrine/doc-2024-08) | PDF du 13 décembre 2024 | 2026-11-05 | 3 |
| [Ordonnance n° 2024-936 du 15 octobre 2024](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050353747) | version initiale, impression de la page Légifrance (pas l'extrait authentifié du JO) | 2026-11-05 | 68 |

Non inclus : les Q&A de l'ESMA (en anglais, non contraignantes, accès manuel nécessaire), DORA, le paquet anti-blanchiment, les actes de niveau 2 de MiCA, le Code monétaire et financier consolidé.

## Méthode

1. **Découpage par structure juridique** : un passage par article ou par paragraphe numéroté, une définition par point, les notes de bas de page à part. Le texte reste mot pour mot.
2. **Recherche** : embeddings bge-m3 (cosinus) par défaut ; BM25 écrit à la main et fusion RRF disponibles.
3. **Refus, première couche** : si le meilleur passage est trop éloigné de la question (cosinus sous 0,59), refus sans appeler le modèle.
4. **Génération contrainte** : `qwen3.5:9b` via Ollama ne produit que « répondre ou refuser », un motif et des **étiquettes de passages** (schéma JSON). Il ne peut pas écrire de citation.
5. **Contrôles du système** : étiquettes valides, réponse non tronquée, nombres de la réponse retrouvés dans les passages cités. Sinon, refus de sécurité.
6. **Affichage** : le texte des citations vient de la base, jamais du modèle. L'avertissement figure dans chaque réponse de l'API et en permanence dans l'interface.

Détails et alternatives : [docs/choix-techniques.md](docs/choix-techniques.md).

## Évaluation et résultats mesurés

42 questions en JSONL ([eval/questions.jsonl](eval/questions.jsonl)), chacune avec des extraits de référence **vérifiés mot pour mot par un test** : 15 pour le réglage (« dev »), 27 pour un test mis de côté. 12 ne sont pas répondables : 6 hors corpus et 6 pièges (texte inexistant, demande d'avis sur un cas particulier), dont 8 dans le dev et 4 dans le test. Les règles de réussite ont été écrites avant les premières exécutions : [docs/regles-notation.md](docs/regles-notation.md). Les chiffres viennent des scripts `eval/`, rapports datés dans `eval/reports/`. Les effectifs sont petits : l'intervalle de Wilson à 95 % est donné.

### Recherche (test, 23 questions répondables : le bon passage est-il dans les 5 premiers ?)

| Mode | recall@5 | Wilson 95 % | MRR@10 |
|---|---|---|---|
| BM25 | 17/23 | 0,54 à 0,87 | 0,69 |
| Vecteurs (bge-m3) | 22/23 | 0,79 à 0,99 | 0,79 |
| Hybride (RRF) | 18/23 | 0,58 à 0,90 | 0,76 |

### Assistant complet (test, 27 questions)

| Configuration | Répondues et sourcées | Refus justifiés hors corpus | Refus d'avis juridique | Total |
|---|---|---|---|---|
| Hybride, seuil 0,59 (**fixée avant de lire le test**) | 18/23 | 2/2 | 2/2 | 22/27 |
| Vecteurs, seuil 0,59 (**livrée, mesurée après avoir vu le test : exploratoire**) | 21/23 | 2/2 | 1/2 | 24/27 |

- **Réponses correctes** (notation de l'assistant, non vérifiée par Louis, configuration livrée) : 19 sur 23 questions répondables (Wilson 95 % : 0,63 à 0,93). Deux réponses sourcées sont fausses : q035 (source juste, définition prise à un paragraphe voisin) et q040 (énumération généralisée à tort).
- **Faux refus** (configuration livrée) : 1 sur 23 répondables (q015). Une réponse sourcée sur le mauvais paragraphe (q028) et un refus avec le mauvais motif (q024 : `hors_corpus` au lieu de `avis_juridique`). Le dev (15 questions, configuration livrée) donne 14/15 ; l'échec est un faux refus sur une question à deux volets (q016).
- Un échec de format a produit deux refus de sécurité en configuration hybride (q025, q031).

### Lecture honnête

- **Aucune question n'a été écrite à la main par l'auteur du dépôt** : 23 ont été proposées par l'assistant IA (Claude) puis validées une par une par l'auteur ; 19 ont été choisies par l'assistant sur délégation, sans relecture individuelle. La même source a écrit les questions et une grande partie du système : biais probable, non mesuré.
- **Le test a été lu trois fois** (recherche, hybride, vecteurs) : la configuration livrée a été choisie après avoir vu le test, même si le jeu de réglage indiquait déjà que les vecteurs seuls faisaient au moins aussi bien. Un jeu neuf est nécessaire pour une mesure propre.
- **Petits effectifs** : 23 à 27 questions, intervalles larges.
- **Sensibilité à la formulation** : sur 10 reformulations, 8 retrouvent le bon passage, mais 2 sont refusées à tort par le seuil. Choix assumé : mieux vaut un faux refus qu'une réponse non fondée ([analyse](docs/analyse-erreurs.md)).
- **« Sourcé » n'est pas « correct »** : une citation exacte peut accompagner une réponse inexacte. Affichez et lisez le texte cité.

## Limites

Liste détaillée et datée : [docs/limites.md](docs/limites.md). L'essentiel :

- Textes non consolidés : les modifications postérieures à la version du Journal officiel ne sont pas prises en compte.
- L'ordonnance est un texte de modification (« le 2° est supprimé ») : une réponse ne donne pas l'état actuel du Code monétaire et financier.
- Le contrôle des nombres est une heuristique ; il ne détecte pas une phrase fausse qui n'emploie que des nombres présents.
- Corpus restreint : MiCA, règlement 2023/1113, orientations de l'ABE, une position de l'AMF, une ordonnance.
- Non vérifié : l'effet de `presence_penalty` dans l'API de chat d'Ollama ; le comportement d'Ollama quand le prompt dépasse le contexte (contrôlé par le système).

## Structure

```
data/sources.yaml     registre des sources (URL, version, date, hash)
backend/app/          chunking, retrieval, generation (schéma, prompt, contrôles), api (FastAPI)
backend/tests/        96 tests
frontend/             interface Next.js (TypeScript)
eval/                 questions.jsonl, run_retrieval.py, run_generation.py, calibrer_seuil.py, probe_paraphrases.py, reports/
scripts/              telecharger.py (téléchargement et vérification des hash)
docs/                 cadrage, choix techniques, règles de notation, analyse d'erreurs, limites, temps
```

## Licence

Code sous licence MIT ([LICENSE](LICENSE)). Les textes réglementaires ne sont pas redistribués dans ce dépôt et restent soumis aux conditions de réutilisation de leurs éditeurs.
