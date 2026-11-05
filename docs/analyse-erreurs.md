---
titre: Analyse des erreurs
date_derniere_mise_a_jour: 2026-11-05
---

Ceci n'est pas un conseil juridique. Ce document décrit des échecs mesurés, un par un, avec leur cause constatée.

Légende : « test » désigne le jeu figé (27 questions), « dev » le jeu de réglage (15 questions). Les rapports bruts sont dans `eval/reports/`. Les notes de justesse sont des **notations de l'assistant, non vérifiées par Louis**.

## 1. Test figé, configuration hybride (lecture officielle, 22/27 sur les décisions)

Cinq échecs sur 23 questions répondables. Aucun n'est dû au modèle seul : le passage de référence n'était pas dans les 5 premiers.

| Question | Cause constatée | Comportement |
|---|---|---|
| q006 (jeton se référant à un ou des actifs) | la définition (article 3, point 6) absente des 5 premiers | réponse fausse sourcée par l'article 43 : le texte cité est réel, mais il parle d'un autre sujet |
| q027 (plate-forme de négociation) | définition absente ; 5 passages de l'article 76 | réponse sur l'article 76, citations réelles mais hors sujet |
| q028 (offres dispensées de livre blanc) | l'article 4 est retrouvé mais pas le bon paragraphe (p7 et p8 au lieu de p2) | réponse sur un autre cas de l'article 4 |
| q025, q031 | passage de référence absent ; le modèle veut refuser mais écrit `repondre` sans citation, deux fois | refus de sécurité `echec_format` |

Constat : la fusion RRF a fait baisser le rappel par rapport au vectoriel seul (18/23 contre 22/23) parce que BM25, mauvais sur les définitions (17/23 au total ; une seule des 5 définitions MiCA du test, q005, est retrouvée dans les 5 premiers), tire le classement vers le bas.

## 2. Test, configuration livrée (vectoriel, seuil 0,59) : lecture exploratoire, 24/27 sur les décisions

Réalisée après avoir vu le test hybride : à lire comme post hoc.

| Question | Cause constatée |
|---|---|
| q015 (période transitoire et règlement 2023/1113) | la note AMF qui contient la réponse n'est pas retrouvée ; le modèle refuse (faux refus) |
| q024 (« ma plateforme est-elle conforme à l'article 59 ? ») | l'article 59 n'est pas retrouvé par la recherche vectorielle ; le modèle refuse avec le motif `hors_corpus` au lieu de `avis_juridique`. BM25 aurait retrouvé « article 59 » |
| q028 | même échec qu'en hybride |

**Justesse du contenu** (notation de l'assistant, non vérifiée par Louis) sur les 21 réponses sourcées : 19 correctes, 2 fautives.

- **q035** : la définition du règlement 2023/1113 (article 3, point 20) n'a été ni retrouvée ni citée : parmi les cinq passages envoyés, il n'y avait que des paragraphes des orientations de l'ABE, et le modèle n'en a cité qu'un (le paragraphe 77). La réponse donne comme définition de l'adresse auto-hébergée une formule tirée d'un paragraphe voisin (le 86). Les contrôles de citation et de nombres ne l'attrapent pas, et la règle « au moins une citation de référence » l'a comptée comme sourcée parce que le paragraphe 77, seconde référence de la question, était cité. C'est une faiblesse de la règle de notation, pas seulement du système.
- **q040** : la réponse écrit « articles 20 à 23 » alors que les articles 20 et 21 ne sont concernés qu'en partie. Généralisation exagérée d'une énumération.
- **Détails non vérifiés** : q013, q033 et q034 ajoutent des précisions au-delà de la question (taux de change, vérifications, évaluation du risque) qui semblent provenir de paragraphes voisins ; je n'ai pas vérifié chacune.

Donc « réponses correctes » : 19 sur 23 questions répondables (Wilson 95 % : 0,63 à 0,93), à comparer aux 21 sur 23 « répondues et sourcées ».

## 3. Dev : cas marquants

- **q004** (définition de crypto-actif) : classée 503e par BM25 et 68e par les vecteurs tant que l'article 3 était découpé en 7 blocs de 3 500 caractères. Corrigé en découpant les définitions par point (51 pour MiCA, 24 pour le règlement 2023/1113).
- **q019** (date de l'AMLR) : le modèle a refusé correctement, mais mon contrôle des nombres a rejeté son refus parce qu'il répétait « 2024/1624 », nombre de la question. Défaut de mon contrôle, corrigé (nombres de la question autorisés).
- **q043 et q019 au second run** : refus corrects rejetés parce qu'ils mentionnaient des textes retrouvés mais non cités, ou une étiquette « (P5) ». Corrigé : les nombres d'un refus sont comparés à tous les passages retrouvés, et les étiquettes sont remplacées par la référence lisible.
- **q016** (date d'application et application par l'AMF) : en vectoriel seul, la position AMF n'est pas dans les 5 premiers ; le modèle refuse toute la question au lieu de répondre à la moitié. Limite sur les questions à deux volets.
- **Gemma 4 (12 Go)** : sur le dev avec le même prompt, il répond au lieu de refuser (q037, q042, q043) et confond le schéma (décision `repondre` avec un motif de refus). Non retenu ; le choix final a de toute façon été fait sur la simplicité et le coût.

## 4. Sensibilité à la formulation (sonde exploratoire, 10 reformulations)

- Recall@5 : vectoriel 8/10, hybride 8/10, BM25 3/10. Les modes se complètent : BM25 retrouve l'article 143 que le vectoriel manque, le vectoriel retrouve les dates et définitions que BM25 manque.
- Deux reformulations correctes sur dix (cosinus 0,553 et 0,586) tombent sous le seuil de 0,59 et sont refusées par la couche 1 avant même le modèle.
- Essayer 0,52 (qui garde ces deux reformulations) a fait répondre le modèle à q039 (orientations ESMA, hors corpus) par une affirmation **non fondée** citant deux articles sans rapport, et cette réponse passe tous les contrôles automatiques. Décision : rester à 0,59 et préférer un faux refus à une fausse réponse. L'interface suggère de reformuler.

## 5. Ce que les contrôles automatiques n'attrapent pas

- Une phrase fausse qui n'emploie que des nombres présents dans les passages cités (q039 à 0,52, q035).
- Une réponse construite sur le mauvais paragraphe du bon article (q028).
- Les nombres écrits en lettres.
- Tout cela justifie qu'une réponse affiche **le texte exact des passages cités** : l'utilisateur peut vérifier lui-même.

## 6. Pistes, non faites faute d'un jeu de test neuf

- Fusion de recherche pondérée ou « vectoriel d'abord, BM25 en renfort pour les références explicites (« article N ») », à mesurer sur un nouveau jeu.
- Joindre le passage voisin (paragraphe précédent et suivant) à un article retrouvé.
- Réponse partielle sur les questions à deux volets.
- Un second contrôle de fidélité (par exemple vérifier que chaque phrase de la réponse a un appui dans un passage cité), qui reste à concevoir et à mesurer.
