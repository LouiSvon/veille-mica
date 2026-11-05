---
titre: Choix techniques, alternatives et phrases pour l'oral
date_derniere_mise_a_jour: 2026-11-05
---

Ceci n'est pas un conseil juridique. Pour chaque choix : ce qui a été retenu, les alternatives, le compromis, ce que la mesure a dit, une phrase pour l'oral, et ce qu'il faut maîtriser pour le défendre.

## Vue d'ensemble

Textes officiels français → découpage par unité citable → recherche (vecteurs bge-m3, éventuellement BM25) → refus couche 1 (seuil de cosinus) → génération contrainte par schéma (qwen3.5:9b via Ollama) → contrôles du système (citations, nombres) → réponse avec le texte exact des passages cités. Tout est local.

## 1. Découpage par structure juridique

- **Retenu** : un passage par article, ou par paragraphe numéroté si l'article dépasse 3 500 caractères ; une définition par point (« article 3, point 5 ») ; un paragraphe par passage pour les orientations ; les notes de bas de page en passages à part ; les annexes et les lignes géantes coupées aux fins de phrase.
- **Alternatives** : fenêtres de taille fixe avec recouvrement.
- **Compromis** : respecte ce qu'un juriste cite, mais produit des passages de tailles inégales (de 20 à 5 700 caractères).
- **Ce que la mesure a dit** : le découpage par blocs de 3 500 caractères noyait les définitions (q004 classée 503e en BM25, 68e en vecteurs) ; le découpage par point l'a corrigé. Le test positif « aucune ligne perdue » a attrapé un contrôle vide de sens dans mon premier essai.
- **Phrase pour l'oral** : « Un juriste cite un article ou un point, donc mon unité de recherche est celle qu'il cite. »
- **À maîtriser** : structure d'un règlement UE (titres, articles, paragraphes, points), pourquoi un passage trop gros noie le signal d'un embedding.

## 2. Embeddings : bge-m3 via Ollama

- **Retenu** : bge-m3 (567 M de paramètres, contexte de 8 192 tokens, plus de 100 langues, environ 1,2 Go), vecteurs denses de 1 024 dimensions, normalisés, cosinus par produit scalaire avec numpy, cache sur disque.
- **Alternatives** : qwen3-embedding, nomic-embed-text-v2-moe, snowflake-arctic-embed2.
- **Compromis** : bon en français, mais l'API d'embedding d'Ollama ne décrit que des vecteurs denses (pas de vecteurs creux) : BM25 reste un composant à part.
- **Phrase pour l'oral** : « Les embeddings retrouvent le sens, y compris quand la question n'emploie pas les mots du texte. »
- **À maîtriser** : similarité cosinus, normalisation, pourquoi les cosinus de bge-m3 sont compressés entre 0,5 et 0,8 (donc un seuil de refus fragile).

## 3. Recherche : vecteurs seuls par défaut, BM25 maison, fusion RRF disponible

- **Retenu par défaut** : vecteurs seuls. BM25 (Okapi, écrit à la main, accents et pluriels normalisés) et la fusion RRF restent disponibles dans le code.
- **Alternatives** : LanceDB (hybride embarqué, vérifié dans sa documentation), Qdrant (hybride vérifié en mode serveur, mode local non vérifié), Chroma et pgvector (non vérifiés ici).
- **Compromis** : avec 863 passages, une base vectorielle n'apporte rien ; le code est court et chaque ligne s'explique. Si le corpus grossit, LanceDB serait l'étape suivante.
- **Ce que la mesure a dit** : sur le test figé (23 questions répondables), recall@5 de 22/23 en vectoriel, 18/23 en hybride, 17/23 en BM25. L'hybride par défaut, fixé avant le test, était donc un mauvais choix ; le dev le laissait déjà voir (MRR 1,00 contre 0,93) et je ne l'avais pas appliqué. Le vectoriel est devenu le défaut après, et sa mesure de génération est étiquetée exploratoire. La sonde de reformulations montre que BM25 rattrape des cas que le vectoriel manque : une fusion mieux conçue reste la meilleure piste.
- **Phrase pour l'oral** : « J'ai comparé trois configurations sur un jeu mis de côté. L'hybride que j'attendais était moins bon que les vecteurs seuls ; je l'ai gardé en option et je le dis. »
- **À maîtriser** : BM25 (fréquence, rareté, longueur), RRF (somme des 1/(k+rang), insensible à l'échelle des scores), recall@k, MRR, intervalle de Wilson.

## 4. Pas de reranking

- **Retenu** : aucun. Décision de Louis du 2026-11-05.
- **Alternatives** : cross-encoder en Python hors Ollama (Ollama n'en documente pas, absence non prouvée).
- **Compromis** : plus simple et 100 % via Ollama ; la mesure montre que des passages de référence manquent aux 5 premiers (cause des erreurs), donc un reranker aurait pu aider, à mesurer sur un jeu neuf.
- **Phrase pour l'oral** : « Je mesure avant d'ajouter une brique ; je sais où elle aiderait, je ne l'ai pas encore prouvé. »

## 5. Génération : qwen3.5:9b, sortie contrainte par un schéma

- **Retenu** : `qwen3.5:9b` (9,7 G de paramètres, Q4_K_M, 6,6 Go), déjà installé. Choix de Louis : le plus simple et le plus économique. Température 0, graine 7, contexte 16 384 tokens, réflexion désactivée, schéma JSON passé au paramètre `format` d'Ollama.
- **Alternatives** : `gemma4:12b-it-qat` (7,2 Go) a été comparé sur le dev avec le même prompt : il répond au lieu de refuser sur plusieurs questions hors corpus et d'avis, et confond le schéma ; plus lent. Écarté sans pousser plus loin.
- **Compromis** : un modèle de 9 G de paramètres est rapide (3 à 7 s par question sur cette machine) mais peut se tromper de paragraphe ou généraliser (q035, q040).
- **Ce que la mesure a dit** : voir `docs/analyse-erreurs.md`. Non documenté et non vérifié : l'effet de `presence_penalty` dans `/api/chat` ; le comportement d'Ollama quand le prompt dépasse `num_ctx` (le système contrôle donc `prompt_eval_count` et `done_reason`).
- **Phrase pour l'oral** : « Le modèle ne décide que de répondre ou de refuser et de pointer des étiquettes de passages ; le texte cité vient toujours de ma base. »
- **À maîtriser** : quantification, fenêtre de contexte, sorties structurées (JSON Schema), pourquoi température 0 et graine fixe donnent des rapports reproductibles.

## 6. Citations : étiquettes validées, texte issu de la base

- **Retenu** : le modèle renvoie des étiquettes P1 à Pk ; le schéma envoyé à Ollama énumère exactement les étiquettes du prompt ; le système vérifie encore, remplace les étiquettes par des références lisibles (« article 3, point 5 ») et affiche le texte exact, l'URL, la version, la date de consultation et le statut contraignant (« statut non vérifié » plutôt qu'un oui ou un non quand l'information manque).
- **Ce que la mesure a dit** : cette garantie tient (aucune citation inventée) mais elle ne garantit pas que la réponse soit fidèle au passage (q035).
- **Phrase pour l'oral** : « Une citation ne peut pas être inventée, mais elle peut être mal utilisée ; c'est pourquoi je montre le texte exact à côté de la réponse. »

## 7. Refus en deux couches, plus des contrôles

- **Couche 1** : si le cosinus du meilleur passage est sous 0,59, refus sans appeler le modèle. Règle écrite avant la valeur (plus petit cosinus répondable du dev moins 0,03).
- **Couche 2** : le modèle refuse avec un motif (`hors_corpus`, `passages_insuffisants`, `avis_juridique`).
- **Contrôles** : citations valides, réponse tronquée ou prompt au niveau du contexte rejetés, nombres de la réponse retrouvés dans les passages cités (ou, pour un refus, dans les passages retrouvés ou dans la question).
- **Compromis mesuré** : à 0,52, une réponse non fondée est passée ; à 0,59, 2 reformulations correctes sur 10 sont refusées. Choix : privilégier le faux refus.
- **Phrase pour l'oral** : « Trois garde-fous indépendants : un seuil avant le modèle, le modèle lui-même, puis des contrôles après. Aucun ne suffit seul, et j'ai montré un cas qu'aucun ne bloque. »

## 8. Évaluation

- **Retenu** : 42 questions en JSONL (15 dev, 27 test), extraits de référence vérifiés mot pour mot par un test, règles de réussite écrites avant la première exécution, effectifs bruts et intervalle de Wilson, dossiers de rapports datés.
- **Limite importante** : 23 questions validées une par une par Louis, 19 choisies par l'assistant sur délégation ; **aucune n'a été écrite par Louis**. Détails dans le README.
- **Phrase pour l'oral** : « Sur 23 questions, un point de pourcentage ne veut rien dire ; je donne le nombre brut et l'intervalle. »

## 9. Application locale

- **Retenu** : FastAPI (API `/ask` et `/health`, CORS limité à localhost:3000), Next.js 16 en TypeScript (une page, avertissement permanent, citations dépliables avec lien source). Pas de démo en ligne.
- **À maîtriser** : CORS, validation d'entrée (3 à 1 000 caractères), pourquoi le texte cité est affiché par le serveur et jamais produit par le modèle.

## Écarts avec le cadrage initial (`docs/cadrage.md`)

- Candidats de génération : le cadrage proposait qwen3:14b, gemma3:12b et mistral-small3.2:24b, à télécharger. Ils ne l'ont pas été : des modèles déjà installés ont été utilisés (`qwen3.5:9b`, `gemma4:12b-it-qat`).
- Recherche : l'hybride était la piste par défaut ; le vectoriel seul est devenu le défaut après mesure.
- Q&A ESMA : non incluses (voir `docs/limites.md`).
- Estimation de 32 h : le temps réel n'a pas été mesuré, voir `docs/temps.md`.
