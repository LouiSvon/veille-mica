"""Contrôle avant livraison : l'interface ne doit imiter ni l'identité de l'État ni nommer un tiers.

Usage : python scripts/controle_identite.py [racine]
Code de sortie 0 si rien n'est trouvé, 1 sinon.
"""
import re
import sys
from pathlib import Path

IGNORES = {".git", "node_modules", ".venv", ".next", "__pycache__", ".pytest_cache", "raw", "processed", "reports"}
EXTENSIONS = {".ts", ".tsx", ".css", ".html", ".md", ".yaml", ".yml", ".json", ".py", ".mjs", ".js"}
# Les mots sont assemblés pour que ce fichier ne se signale pas lui-même.
MOTIFS = {
    "dsfr": re.compile("ds" + "fr", re.I),
    "police ou logo d'État": re.compile("maria" + "nne", re.I),
    "bloc-marque": re.compile("république" + r"\s+française|liberté,?\s+égalité", re.I),
    "classe de système de design d'État": re.compile(r"""class(?:Name)?\s*=\s*["'{`][^"'`]*\bfr-"""),
    "tiers nommé": re.compile("doors" + "3", re.I),
}
NOMS_INTERDITS = ("maria" + "nne", "ds" + "fr")
# Fichiers où la mention est légitime : la documentation de design explique l'interdit.
EXCLUS = {"design.md", "controle_identite.py", "journal-decisions.md"}


def balayer(racine: Path) -> list[str]:
    trouves = []
    for chemin in racine.rglob("*"):
        if any(p in IGNORES for p in chemin.relative_to(racine).parts) or not chemin.is_file():
            continue
        if any(n in chemin.name.lower() for n in NOMS_INTERDITS):
            trouves.append(f"{chemin}: nom de fichier interdit")
            continue
        if chemin.suffix not in EXTENSIONS or chemin.name in EXCLUS:
            continue
        try:
            texte = chemin.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for nom, motif in MOTIFS.items():
            if motif.search(texte):
                trouves.append(f"{chemin}: {nom}")
    return trouves


if __name__ == "__main__":
    racine = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    resultats = balayer(racine)
    print("\n".join(resultats) if resultats else "OK : aucune imitation ni nom de tiers détecté.")
    sys.exit(1 if resultats else 0)
