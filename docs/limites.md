---
titre: Limites connues du projet veille-mica
date_derniere_mise_a_jour: 2026-11-05
---

Ceci n'est pas un conseil juridique. Ce document liste les limites constatées, pas des hypothèses.

## Corpus

- Les textes de MiCA et du règlement 2023/1113 sont ceux du Journal officiel, non consolidés. Une version consolidée de MiCA existe (vue en recherche, `02023R1114-20240109`) : les modifications postérieures au texte publié ne sont pas prises en compte. Écart exact : à mesurer.
- Le droit évolue : l'assistant doit afficher la date de consultation et la version de chaque source citée.
- Les Q&A de l'ESMA seront en anglais et non contraignantes (décision du 2026-11-05). Elles ne sont pas encore dans le corpus.
- Ordonnance 2024-936 : téléchargement manuel du PDF « Extrait du JO » nécessaire (Légifrance répond HTTP 403 aux scripts). Pas encore dans le corpus.
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
