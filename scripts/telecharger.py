"""Télécharge les textes du registre data/sources.yaml dans data/raw/ et vérifie leur empreinte.

Usage :
    python scripts/telecharger.py                 # télécharge ce qui manque
    python scripts/telecharger.py --verifier      # compare les hash sans télécharger
    python scripts/telecharger.py --id mica       # une seule source
    python scripts/telecharger.py --forcer        # retélécharge même un fichier déjà présent et identique

Règles : une requête par seconde au plus, un fichier vide est une erreur
(EUR-Lex répond par un contrôle anti-robot vide, code 202), le registre n'est
jamais modifié sans que le script l'annonce.
"""
import argparse
import hashlib
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent
REGISTRE = RACINE / "data" / "sources.yaml"
DOSSIER_BRUT = RACINE / "data" / "raw"
PAUSE_SECONDES = 1.0
AGENT = "veille-mica/0.1 (projet personnel de veille réglementaire)"


class TelechargementInvalide(Exception):
    pass


def sha256_octets(donnees: bytes) -> str:
    return hashlib.sha256(donnees).hexdigest()


def telecharger(url: str, en_tetes: dict, delai: int = 90) -> bytes:
    requete = urllib.request.Request(url, headers={"User-Agent": AGENT, **en_tetes})
    with urllib.request.urlopen(requete, timeout=delai) as reponse:
        donnees = reponse.read()
    if not donnees:
        raise TelechargementInvalide(f"réponse vide pour {url} (contrôle anti-robot ?)")
    return donnees


def charger_registre(chemin: Path = REGISTRE) -> dict:
    return yaml.safe_load(chemin.read_text(encoding="utf-8"))


def traiter(source: dict, dossier: Path, verifier_seulement: bool, forcer: bool = False) -> str:
    cible = dossier / str(source["fichier"])
    if verifier_seulement:
        if not cible.exists():
            return "absent"
        attendu = source["sha256"]
        if attendu == "a_fournir":
            return "hash a_fournir"
        return "identique" if sha256_octets(cible.read_bytes()) == attendu else "DIFFERENT"
    if source["url_telechargement"] == "a_fournir" or source["fichier"] == "a_fournir":
        return "ignoré (url a_fournir)"
    if not forcer and cible.exists() and source["sha256"] != "a_fournir" and sha256_octets(cible.read_bytes()) == source["sha256"]:
        return "déjà présent, hash identique : non retéléchargé"
    donnees = telecharger(source["url_telechargement"], source.get("en_tetes") or {})
    dossier.mkdir(parents=True, exist_ok=True)
    cible.write_bytes(donnees)
    empreinte = sha256_octets(donnees)
    attendu = source["sha256"]
    if attendu == "a_fournir":
        return f"téléchargé, {len(donnees)} octets, sha256 {empreinte} (à inscrire dans le registre, le {date.today()})"
    return f"téléchargé, {'identique' if empreinte == attendu else 'DIFFERENT'} au registre"


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--id")
    p.add_argument("--verifier", action="store_true")
    p.add_argument("--forcer", action="store_true", help="retélécharge même un fichier présent et identique")
    args = p.parse_args(argv)
    sources = charger_registre()["sources"]
    if args.id:
        sources = [s for s in sources if s["id"] == args.id]
        if not sources:
            print(f"source inconnue : {args.id}", file=sys.stderr)
            return 2
    code = 0
    for i, s in enumerate(sources):
        try:
            print(f"{s['id']}: {traiter(s, DOSSIER_BRUT, args.verifier, args.forcer)}")
        except Exception as e:  # une source en échec n'arrête pas les autres
            print(f"{s['id']}: ECHEC {type(e).__name__}: {e}", file=sys.stderr)
            code = 1
        if not args.verifier and i < len(sources) - 1:
            time.sleep(PAUSE_SECONDES)
    return code


if __name__ == "__main__":
    sys.exit(main())
