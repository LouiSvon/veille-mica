---
titre: Limites connues du projet veille-mica
date_derniere_mise_a_jour: 2026-11-05
---

Ceci n'est pas un conseil juridique. Ce document liste les limites constatées, pas des hypothèses.

## Corpus

- Les textes de MiCA et du règlement 2023/1113 sont ceux du Journal officiel, non consolidés. Une version consolidée de MiCA existe (vue en recherche, `02023R1114-20240109`) : les modifications postérieures au texte publié ne sont pas prises en compte. Écart exact : à mesurer.
- Le droit évolue : l'assistant doit afficher la date de consultation et la version de chaque source citée.
- Les Q&A de l'ESMA seront en anglais et non contraignantes (décision du 2026-11-05). Elles ne sont pas encore dans le corpus.
- Ordonnance 2024-936 : Légifrance répond HTTP 403 aux scripts, y compris depuis la page ouverte dans un navigateur automatisé. Le corpus contient l'impression Firefox de la page « VERSION INITIALE » faite à la main par Louis le 2026-11-05 (71 pages), pas l'extrait authentifié du Journal officiel. Son hash est celui de cette impression : une autre impression donnera un autre hash. Seule la version initiale est couverte (pas les versions consolidées du Code monétaire et financier qu'elle modifie).
- La stabilité du hash de la position AMF a été vérifiée sur 3 téléchargements rapprochés (quelques secondes), pas sur plusieurs jours.

## Découpage (constaté le 2026-11-05)

- Orientations EBA : le tableau de définitions du paragraphe 9 est mal rendu par l'extraction. Le nom du terme défini (par exemple « Risque ») se retrouve au milieu de sa définition. Les passages de ce paragraphe sont à vérifier à la main avant de poser des questions de définition sur ce texte.
- Orientations EBA : le paragraphe 47 fait environ 4 200 caractères, au-dessus du seuil de 3 500 utilisé pour les articles. Il n'est pas redécoupé.
- Les notes de bas de page sont des passages à part (type `note`), non rattachés au paragraphe qui les appelle. Un passage de note se cite par sa page.
- L'extraction des PDF dépend de `pdftotext` (poppler) et de la mise en page de chaque document : l'en-tête courant est retiré par un préfixe propre à chaque source.
- Le seuil de 3 500 caractères est un choix de départ, non mesuré. Il sera réévalué sur les questions de développement.

## Vérifications faites

- MiCA : 149 articles et 6 annexes retrouvés, `tests/test_chunking.py`.
- Règlement 2023/1113 : 40 articles retrouvés.
- Orientations EBA : paragraphes 1 à 94 contigus ; aucune ligne du corps perdue (hors page de titre), avec un test positif qui prouve que le détecteur signale un passage retiré.

## Recherche : constats qualitatifs du 2026-11-05 (6 questions, ce ne sont pas des scores)

- bge-m3 via Ollama : vecteurs denses de 1024 dimensions, 673 Mo en mémoire, 100 % GPU (`ollama ps`). Environ 20 s pour embedder 708 passages.
- Question « Que dit l'article 143 de MiCA ? » : BM25 classe l'article 143 premier, la recherche vectorielle ne le trouve pas dans les 3 premiers, et la fusion RRF le descend sous l'article 144. La fusion dilue un résultat lexical exact. Piste à mesurer sur les questions de développement : pondérer BM25, ou détecter une référence explicite (« article N »).
- Question « Jusqu'à quand les prestataires déjà actifs peuvent-ils continuer… » : BM25 trouve l'article 143 en premier, la recherche vectorielle ne le trouve pas, l'hybride le met 3e.
- Question hors corpus (« capitale de la France ») : les trois modes renvoient quand même des passages. Le score de fusion RRF n'a pas de sens absolu : le refus par seuil (lot D) devra s'appuyer sur le cosinus et le score BM25 bruts, calibrés sur des questions hors corpus.
- Les identifiants de passages d'un article sans numéro de paragraphe mais coupé en morceaux ont une forme peu lisible (`tfr-art-3-p-s1`). Ils restent uniques.

## Contrôle indicatif sur 7 questions de développement non validées (2026-11-05)

Ce ne sont pas des scores : les questions sont proposées par l'assistant et pas encore validées par Louis, n = 7.
- Les trois modes retrouvent le passage de référence dans les 5 premiers pour 6 questions sur 7.
- La question de définition « Comment MiCA définit-il un crypto-actif ? » (q004) n'est retrouvée par aucun mode dans les 10 premiers : le terme « crypto-actif » apparaît dans presque tous les passages et le passage des définitions (article 3, morceau 1) ne se distingue pas. À reprendre après validation : étiquette de définition dans le texte indexé, ou recherche sur le terme défini.
- Défaut corrigé pendant la rédaction : l'en-tête courant de la page 2 de la position AMF se retrouvait au milieu d'une phrase. Retiré, avec un test.

## Correction de q004 : définitions découpées par point (2026-11-05)

- Cause constatée : l'article 3 de MiCA était découpé en 7 morceaux de 3 500 caractères contenant chacun une douzaine de définitions. Le passage de « crypto-actif » était classé 503e par BM25 et 68e par les vecteurs.
- Correction structurelle, pas un réglage sur la question : toute liste de définitions numérotées (« N) «terme»: ... », au moins 5 points) devient un passage par point. Résultat mesuré : MiCA article 3, 51 points ; règlement 2023/1113 article 3, 24 points. Une définition se cite par son point (« article 3, point 5 »).
- Mesure sur le dev après correction (n = 7, Wilson 95 %) : vecteurs recall@5 7/7 (0,65 à 1,00), MRR 1,00 ; hybride 7/7, MRR 0,93 ; BM25 6/7, MRR 0,64. BM25 ne retrouve toujours pas q004 : la question dit « définit » et l'étiquette dit « définition », deux racines différentes pour la tokenisation actuelle.
- Sur ce lot, la recherche vectorielle seule fait au moins aussi bien que l'hybride. Avec n = 7 aucune différence n'est établie. La comparaison sérieuse attend le jeu complet.
- Le plus long passage est la définition 33 (« État membre d'origine », 5 707 caractères) : une seule définition avec ses sous-points.
- Le rapport du dev d'avant correction (6/7 pour les trois modes) est dans l'historique git (commit d9127b6) ; le fichier du jour a été remplacé.
- Trois questions validées (q004, q005, q006) avaient un identifiant de passage qui n'existe plus ; leur identifiant a été mis à jour, la question, la réponse et l'extrait sont inchangés.

## Ordonnance 2024-936 ajoutée au corpus (2026-11-05)

- 50 articles contigus (Titre I : 1 à 33 ; Titre II outre-mer : 34 à 48 ; Titre III : 49 et 50), 68 passages avec les visas. Aucune ligne de contenu perdue, avec un test positif.
- Un passage est un article, ou un groupe de blocs si l'article dépasse 3 500 caractères (les articles qui modifient le Code monétaire et financier sont longs). Les passages découpés ne portent pas le numéro de l'alinéa modifié.
- Le texte des articles est celui d'une ordonnance de modification : il dit « le 2° est supprimé », pas le droit en vigueur résultant. Une réponse tirée de ces passages ne donne pas l'état du Code monétaire et financier aujourd'hui.
- Sur le dev (7 questions répondables), l'ajout de ces 68 passages ne change aucun rang : même recall et même MRR pour les trois modes.

## Q&A de l'ESMA : non incluses dans cette version (2026-11-05)

- La décision initiale était de les inclure (en anglais, non contraignantes, avec mention affichée).
- L'outil de recherche de l'ESMA est une application web sans liste téléchargeable : l'accès retenu était un export Excel manuel, à faire par Louis dans son navigateur. Cet export n'a pas été fait pendant son absence ; automatiser l'exploration des pages était écarté (conditions de réutilisation et `robots.txt` non vérifiés au-delà de `/search/`).
- Conséquence : la note de la position AMF qui cite la Q&A ESMA_QA_2295 reste sans sa source. Aucune question du jeu ne s'appuie sur une Q&A. À faire : exporter, découper, ajouter des questions.

## Évaluation (2026-11-05)

- Aucune question n'a été écrite à la main par l'auteur du dépôt. 23 ont été validées une par une ; 19 sont des questions déléguées (statut `delegue`).
- Le test figé a été lu trois fois : recherche en trois modes, génération en hybride (configuration fixée avant), génération en vectoriel (exploratoire). La configuration livrée n'est donc pas mesurée proprement.
- La notation de justesse du contenu est celle de l'assistant, non vérifiée par Louis.
- Les 10 reformulations de la sonde sont écrites par l'assistant ; la sonde sert à documenter une sensibilité, pas à mesurer une performance.

## Génération (2026-11-05)

- La réponse peut être fausse bien qu'elle cite un passage réel (q035, q040). Le système affiche donc le texte cité à côté de la réponse.
- Deux contrôles n'existent pas : fidélité de chaque phrase au passage, et vérification des nombres écrits en lettres.
- Le seuil de refus (0,59) est dérivé de 7 points du dev. Il refuse à tort environ 2 reformulations correctes sur 10 ; un seuil plus bas a laissé passer une réponse non fondée.
- Les cosinus de bge-m3 sont compressés entre environ 0,5 et 0,8 : la séparation entre répondable et hors corpus par un seuil est fragile.
- Latence mesurée : environ 2 à 7 s par question appelant le modèle (qwen3.5:9b), sur un Mac M5 Pro avec 24 Go. Non mesurée sur une autre machine.
