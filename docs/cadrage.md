---
titre: Cadrage du projet veille réglementaire crypto-actifs (RAG)
date_derniere_mise_a_jour: 2026-11-05
statut: proposition, en attente de validation de Louis
---

Ceci n'est pas un conseil juridique. Ce document décrit un projet logiciel.

Légende : **vérifié** = lu ou confirmé par une source citée ; **mesuré** = compté sur un fichier téléchargé ; **non vérifié** = vu seulement dans une source secondaire, ou pas vu ; **à mesurer** = chiffre à obtenir en exécutant quelque chose ; **à fournir** = donnée que seul Louis peut apporter.

## 0. État réel : du code existe déjà

Les lots 0 et 1 ont été faits avant ce cadrage et sont commités sur la branche `feature/socle` (2 commits, 2026-11-05).

| Existant | Rôle | Devient |
|---|---|---|
| `src/decoupage/decouper.py` | découpe MiCA et TFR en passages | `backend/app/chunking/` |
| `tests/test_decoupage.py` (7 tests) | contrôle des 149 et 40 articles | `backend/tests/` |
| `sources/catalogue.csv` | registre minimal de 2 textes | `data/sources.yaml` (avec hash, version) |
| `pyproject.toml`, `.venv` (uv, Python 3.14) | environnement | `backend/pyproject.toml` |
| `sources/brut/` (non versionné) | textes téléchargés | `data/raw/` (non versionné) |

La migration vers la structure du §3 se fait seulement après ta validation. Aucune ligne de code n'est écrite depuis ta nouvelle consigne.

La question précédente (téléchargement de bge-m3) est retirée : le choix du modèle d'embedding est repris au §4.

Temps réel passé sur les lots 0 et 1 : **non mesuré**. Les horodatages des commits (15:24 et 15:26) ne mesurent pas l'effort. À fournir : ton ressenti de durée. Je tiendrai un journal d'heures `docs/temps.md` à partir de maintenant.

## 1. Textes officiels

Date de vérification : 2026-11-05. Les pages EUR-Lex refusent la lecture web directe ; les textes sont obtenus par `publications.europa.eu/resource/celex/<CELEX>` avec l'en-tête `Accept: application/xhtml+xml` (vérifié, code 200).

### Noyau

| # | Texte | Identifiant | URL | Vérification | Volume |
|---|---|---|---|---|---|
| 1 | Règlement (UE) 2023/1114 (MiCA), texte du Journal officiel | CELEX 32023R1114 | https://eur-lex.europa.eu/eli/reg/2023/1114/oj/fra | téléchargé et lu | mesuré : 149 articles, 6 annexes, 533 passages |
| 2 | Règlement (UE) 2023/1113 (transferts de fonds et de crypto-actifs) | CELEX 32023R1113 | https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32023R1113 | téléchargé et lu | mesuré : 40 articles, 71 passages |
| 3 | EBA, orientations sur la travel rule, version française | EBA/GL/2024/11, 4 juillet 2024 | https://www.eba.europa.eu/sites/default/files/2024-09/6de6e9b9-0ed9-49cd-985d-c0834b5b4356/Travel%20Rule%20Guidelines_Final%20Report%20(EBA.GL_.2024.11)_FR_COR.pdf | existence vue dans une recherche, PDF non encore lu | à mesurer |

Points à connaître sur ces trois textes :
- Dates MiCA, vérifiées dans le texte lu : article 149 (application le 30 décembre 2024, titres III et IV le 30 juin 2024), article 143 paragraphe 3 (transition « jusqu'au 1er juillet 2026 »).
- La page EBA donne une application au 30/12/2024 et une « échéance de conformité » au 27/11/2024, antérieure : incohérence apparente, non résolue.
- Il existe une version consolidée de MiCA (`02023R1114-20240109`, vue en recherche). Elle n'a pas de valeur juridique. Nous utilisons le texte du JO. Le registre et `docs/limites.md` devront dire quelles modifications ultérieures ne sont pas prises en compte : **à mesurer** en comparant avec la consolidation.

### Extension (ordre de priorité proposé)

| Priorité | Texte | URL | Vérification | Volume |
|---|---|---|---|---|
| 1 | AMF, position DOC-2024-08 (reprend les orientations EBA) | https://www.amf-france.org/fr/reglementation/doctrine/doc-2024-08 (page anglaise vue : https://www.amf-france.org/en/regulation/policy/doc-2024-08) | existence et application au 30/12/2024 vues en recherche | à mesurer, court |
| 2 | Ordonnance n° 2024-936 du 15 octobre 2024 relative aux marchés de crypto-actifs | https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050353747 | titre et numéro vérifiés sur Légifrance. Un résumé de recherche citait « 2024-397 » : écart, probablement une erreur de résumé | à mesurer |
| 3 | Règlement (UE) 2022/2554 (DORA) | https://eur-lex.europa.eu/eli/reg/2022/2554/oj/fra | applicable depuis le 17 janvier 2025, vérifié (EUR-Lex, ESMA, AMF via recherche) | à mesurer |
| 4 | Règlements délégués MiCA niveau 2 (liste issue d'une compilation de la Commission, texte brouillé) : 2025/305 (art. 62), 2025/294, 2025/299, 2025/1140, 2025/1142, 2025/416, 2025/417, 2025/414 | à retrouver sur EUR-Lex | numéros non vérifiés un par un | à mesurer |
| 5 | Règlement (UE) 2024/1624 (AMLR) | https://eur-lex.europa.eu/eli/reg/2024/1624/oj/fra | application le 10 juillet 2027, vérifié, sauf 10 juillet 2029 pour certaines entités | à mesurer |
| 6 | Directive (UE) 2024/1640 | https://eur-lex.europa.eu/eli/dir/2024/1640/oj/fra | transposition au 10 juillet 2027, certains points 2026 ou 2029, vérifié | à mesurer |
| 7 | Règlement (UE) 2024/1620 (AMLA) | à retrouver | date d'application **non vérifiée** | à mesurer |
| 8 | Q&A et orientations ESMA et EBA sur MiCA | https://www.esma.europa.eu/publications-and-data/interactive-single-rulebook/mica | page lue, en anglais ; Q&A non contraignantes | à mesurer |
| 9 | Code monétaire et financier (articles L54-10-x et autres) | Légifrance | accès par API PISTE | à mesurer |

Écarté du corpus : le registre intérimaire de l'ESMA (données, pas des textes). Lignes directrices ESMA « applicables en France à partir du 28 juillet 2026 » : **non vérifié**.

Recommandation de périmètre pour tenir le budget : noyau, plus les priorités 1 et 2 (courtes, en français, et elles font le lien avec la France). DORA, AMLR et le reste sont des extensions à décider après les premiers scores.

### Conditions de réutilisation et robots

- EUR-Lex : réutilisation autorisée pour les documents juridiques sous la décision 2011/833/UE ; licence CC BY 4.0 pour le contenu éditorial, les résumés et les textes consolidés (mention de la source et des modifications). Vérifié sur la page de notice légale EUR-Lex, par recherche.
- `robots.txt` d'EUR-Lex et règles de débit : **non vérifié** (lecture vide, `curl` refusé). Nous limitons le débit à une requête par seconde et nous téléchargeons chaque texte une seule fois.
- Légifrance : API gratuite via PISTE, licence ouverte 2.0, quotas, OAuth 2.0. **Il faut un compte PISTE que tu crées toi-même** ; je ne crée aucun compte.
- Textes bruts dans le dépôt : non, tant que la licence de chaque source n'est pas vérifiée. Le dépôt contient un script de téléchargement, le registre `data/sources.yaml` et les empreintes (hash).

## 2. Plan en étapes et heures

Toutes les heures sont des **estimations non mesurées**. Les heures de Louis sont séparées.

| Lot | Contenu | Test réel de fin de lot | Heures (moi) |
|---|---|---|---|
| A | Registre `sources.yaml`, script de téléchargement reproductible avec hash, extraction du PDF EBA, ajout des priorités 1 et 2 | re-téléchargement : hash identiques ; compte d'articles/pages | 3 |
| B | Migration vers `backend/`, chunking étendu (PDF, version du texte, métadonnées) | tests existants + nouveaux, comptes mesurés | 2 |
| C | Recherche : BM25 maison, embeddings, fusion RRF, 3 configurations, recall@k et MRR | rappel sur les 10 questions de développement | 5 |
| D | Génération : sortie structurée (identifiants de passages), contrôle des citations, refus en 2 couches | rejet automatique d'une citation fausse (cas positif et négatif) | 5 |
| E | Jeu d'évaluation 30 à 50 questions (JSONL) : j'en propose 25 à 35, tu en écris 15 | chaque question validée par toi | 4 |
| F | Exécution, intervalles de Wilson, analyse d'erreurs une par une | scores issus du script, non d'une estimation | 3 |
| G | API FastAPI et interface Next.js minimale, avertissement partout | appel réel, capture de l'interface | 4 |
| H | README, `choix-techniques.md`, `limites.md`, Makefile, licence, écart estimation/réel | relecture à froid | 3 |
| | **Total moi** | | **29** |
| | **Total Louis** : écrire 15 questions avec passage source (3 h), valider les autres (2 h) | | **5** |

Le total de 29 h est au bord de ta fenêtre, sans marge, et il n'inclut pas les lots 0 et 1 déjà faits. Il est probable que le réel dépasse 30 h. Coupes, dans cet ordre si nous dérapons :
1. Pas de reranking (il reste dans la liste des pistes, mesuré seulement si le temps le permet).
2. Génération évaluée seulement sur la meilleure configuration de recherche ; les 3 configurations restent comparées sur recall@k et MRR.
3. Pas de LLM juge (la notation est manuelle de toute façon).
4. Extension limitée aux priorités 1 et 2.
5. Interface réduite à un seul écran.

Une extension (par exemple DORA) coûte environ 2 à 3 h chacune : à mesurer sur la première.

## 3. Structure du dépôt (ajustée)

```
veille-mica/
  README.md              but, méthode, résultats mesurés, limites, avertissement
  LICENSE                MIT proposée (tes autres dépôts sont en MIT d'après le journal)
  Makefile               setup, ingest, serve, eval, test
  docs/
    cadrage.md           ce document
    choix-techniques.md  décisions, alternatives, phrases pour l'oral
    analyse-erreurs.md
    limites.md
    temps.md             heures réelles par lot
  data/
    sources.yaml         registre : titre, identifiant, URL, date, version, hash
    raw/                 non versionné
    processed/           non versionné
  backend/
    pyproject.toml
    app/                 chunking, ingestion, retrieval, generation, citations, api
    tests/
  frontend/              Next.js, TypeScript
  eval/
    questions.jsonl
    run_eval.py
    reports/             résultats datés
  scripts/               téléchargement, utilitaires
```

## 4. Choix techniques recommandés

Pour chaque choix : recommandation, alternatives, compromis, phrase pour l'oral, et ce qu'il faut apprendre.

| Choix | Recommandation | Alternatives | Compromis | Phrase pour l'oral | À apprendre |
|---|---|---|---|---|---|
| Découpage | par article, puis paragraphe, puis point (déjà fait) | fenêtres de taille fixe | plus fidèle au droit, passages de tailles inégales | « Un juriste cite un article, donc mon unité de recherche est l'article. » | structure d'un règlement UE |
| Embeddings | **bge-m3** : 567m, contexte 8K, plus de 100 langues, environ 1,2 Go (page Ollama lue) | qwen3-embedding (0.6b, 4b, 8b), nomic-embed-text-v2-moe, snowflake-arctic-embed2 (multilingues) | bge-m3 sur Ollama : l'API d'embedding documentée ne décrit que des vecteurs denses, aucun vecteur creux (non mentionné ; absence non prouvée), donc BM25 est un composant à part | « Les embeddings retrouvent le sens, BM25 retrouve les termes exacts, je fusionne les deux. » | dense vs creux, similarité cosinus |
| Recherche | **BM25 maison + cosinus (numpy) + fusion RRF**, derrière une interface `Retriever`. Corpus : environ 600 passages aujourd'hui | LanceDB (embarqué, recherche plein texte et vecteurs, fusion RRF par défaut, vérifié dans la doc) ; Qdrant (hybride vérifié en mode serveur, **mode local non vérifié**) ; Chroma et pgvector **non vérifiés ici** | maison : peu de code, contrôle du français et des numéros d'articles, mais moins « base de données » sur le CV. LanceDB si le corpus grossit | « À cette taille, une base vectorielle n'apporte rien ; j'ai gardé le code assez court pour l'expliquer ligne par ligne. » | BM25, RRF, normalisation du français |
| Reranking | **aucun au départ** | cross-encoder en Python hors Ollama (bge-reranker-v2-m3 cité par un blog promotionnel, existence non vérifiée) | Ollama n'a pas d'endpoint de rerank dans la documentation consultée (non trouvé, non prouvé absent). Un cross-encoder sort de la règle « tout via Ollama » | « Je mesure d'abord ; je n'ajoute un reranker que si les chiffres le justifient. » | cross-encodeur vs bi-encodeur |
| Génération | choix **mesuré** sur les 10 questions de développement parmi : qwen3:14b (9,3 Go), gemma3:12b (8,2 Go), mistral-small3.2:24b (15 Go, limite) | qwen3:30b et :32b (19 à 20 Go) exclus ; gemma3:27b (17 Go) limite | un modèle de 15 Go partage la mémoire avec l'embedding, le serveur et le système. Le français n'est pas cité nommément sur les fiches Ollama de qwen3, gemma3 et mistral-small3.2 | « J'ai choisi sur mesure, pas sur réputation. » | quantification, mémoire unifiée |
| Citations | le modèle renvoie seulement des identifiants de passages, validés par un schéma Pydantic via le paramètre `format` d'Ollama (vérifié dans la doc) | citations libres | le texte affiché vient toujours de la base ; combinaison avec le mode « thinking » de qwen3 **à tester** | « Le modèle ne peut pas inventer une citation : il ne fait que pointer. » | JSON Schema, Pydantic |
| Refus | seuil de pertinence calibré sur les questions de développement, puis refus explicite du modèle avec motif | refus par prompt seul | un seuil mal réglé produit des faux refus : mesurés | « Deux garde-fous, donc un modèle qui se trompe ne suffit pas. » | calibration d'un seuil |
| Évaluation | JSONL, 10 questions de développement + test figé, intervalles de Wilson | moyenne simple | effectifs petits : on affiche n sur N et l'intervalle | « Sur 40 questions, un point de pourcentage ne veut rien dire ; je donne l'intervalle. » | intervalle de Wilson, recall@k, MRR |

Machine (mesurée) : Apple M5 Pro, 24 Gio de mémoire, Ollama 0.35.0, 527 Gio libres. Sur macOS la mémoire utilisable par le GPU est inférieure à la mémoire totale : preuve à obtenir avec `ollama ps` (répartition GPU/CPU) après téléchargement d'un modèle, seulement avec ton accord.

## 5. Corrections et limites de ce cadrage

- Correction : j'ai écrit plus tôt que la France « a choisi sa propre échéance » (30 juin pour l'AMF contre 1er juillet pour le règlement). C'était une déduction présentée comme un fait. La différence est probablement une question de formulation (« jusqu'au 30 juin » ou « jusqu'au 1er juillet »). Le communiqué AMF du 6 juillet 2026 n'a pas été lu : **non vérifié**.
- Un résumé de recherche de l'AMF cite « ordonnance 2024-397 » ; Légifrance donne 2024-936. Retenu : 2024-936.
- Les Q&A ESMA sont en anglais. Ta règle demande des versions françaises officielles : à trancher (exclure, ou inclure avec une mention « en anglais, non contraignant »).
- Le contenu de l'API Ollama sur le reranking et les vecteurs creux repose sur une page de documentation et une recherche : absence non prouvée.
- Aucune donnée n'a été inventée. Tous les chiffres de ce document sont soit cités avec leur source, soit marqués non vérifié ou à mesurer.

## 6. Décisions à valider

1. Périmètre : noyau + AMF DOC-2024-08 + ordonnance 2024-936, extensions après premiers scores ; Q&A ESMA exclues ou incluses.
2. Reranking : aucun au départ, ou cross-encoder hors Ollama.
3. Recherche : implémentation maison (recommandée) ou LanceDB.
4. Licence : MIT.
5. Compte PISTE pour Légifrance : à créer par toi si l'ordonnance et le Code monétaire et financier entrent dans le périmètre.
