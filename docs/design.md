---
titre: Design de l'interface
date: 2026-11-05
---

# Design de l'interface

## Principe
Papier et encre. Un public d'experts lit vite et vérifie les citations : pas d'effet, pas de décor.

## Ce que l'interface n'est pas
Le registre visuel est celui d'un site institutionnel sobre, pas son identité. Le système de design de l'État est réservé aux sites de l'État (source : page du Service d'information du Gouvernement sur le système de design, consultée le 2026-11-05). Le détail de l'usage de la typographie et du logo de l'État n'a pas été revérifié dans les textes officiels : en cas de doute, ne rien reprendre.
Contrôle automatique avant livraison : `make controle-identite` (aucune occurrence de ces éléments dans le dépôt, ni de nom de tiers). Le pied de page indique : « Projet indépendant, non affilié à une autorité publique. »

## Polices (auto-hébergées, licence SIL OFL 1.1, aucun CDN)
- Titres, réponse et citations : Source Serif 4. Raison : serif de lecture conçue pour le texte continu, lisible à l'écran et à l'impression, ton éditorial sans fantaisie.
- Interface : Source Sans 3. Raison : même famille de dessin que la serif, donc un ensemble cohérent, neutre pour les formulaires et les étiquettes.
- Paquets npm `@fontsource-variable/source-serif-4` et `@fontsource-variable/source-sans-3` (5.3.1, versions épinglées), chargés par `next/font/local`. Sous-ensemble latin.

## Palette
| Rôle | Valeur |
|---|---|
| Papier | #fbfaf7 (secondaire #f2f0ea) |
| Encre | #15171c (texte secondaire #4f5259) |
| Filets | #d6d2c8, 1 px |
| Accent unique | bleu nuit #1b2a4a |
| Refus | bordeaux #7a1f2b (texte et filet, jamais en aplat) |
| Erreur | #a3201a |

Pas d'ombre, pas de dégradé, rayons de 2 px, thème clair uniquement.

## Typographie, quatre niveaux
Titre (serif, 28 à 36 px), section (serif 22 px), étiquette (sans capitales 13 px), texte (sans 16 px ; réponse et citations en serif 17 à 19 px). Colonne de lecture de 720 px.

## Écrans et usages
- Une seule page. Question, exemples en liste de liens, réponse, sources numérotées et dépliables.
- Chaque citation : référence, source, mention « non contraignant » le cas échéant, texte exact, version et date de consultation, bouton « Copier la citation » (texte, référence, source, URL), lien vers la source officielle.
- « Copier la réponse avec ses sources » et « Imprimer ».
- Impression : formulaire et exemples masqués, citations toutes dépliées, question rappelée, avertissement conservé.
- Mouvement : seule transition, 120 ms sur le bouton principal, désactivée si `prefers-reduced-motion`.
- Aucun cookie, aucun traceur, aucune image, aucun appel à un service tiers.

## Accessibilité
Contrastes calculés (formule WCAG, sur le papier #fbfaf7) : encre 17,2:1 ; texte secondaire 7,5:1 ; accent 13,6:1 ; refus 9,8:1 ; erreur 7,2:1 ; bouton principal 14,2:1. Tous au-dessus de 7:1. Éléments dépliables natifs (`details`), focus visible, lien externe annoncé.
