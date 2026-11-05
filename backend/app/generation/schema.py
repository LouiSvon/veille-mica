"""Schéma de la réponse du modèle et de la réponse finale du système.

Le modèle ne renvoie que des décisions et des étiquettes de passages (P1..Pk), jamais de texte de citation.
Le schéma JSON est construit pour chaque requête avec les étiquettes réellement envoyées : une étiquette
inexistante est interdite dès la génération (énumération), et re-vérifiée ensuite par le système.
"""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

AVERTISSEMENT = "Ceci n'est pas un conseil juridique."

Decision = Literal["repondre", "refuser"]
MotifModele = Literal["hors_corpus", "passages_insuffisants", "avis_juridique"]
MotifSysteme = Literal["hors_corpus", "passages_insuffisants", "avis_juridique", "echec_format", "echec_verification", "echec_technique"]


class SortieModele(BaseModel):
    """Ce que le modèle a le droit de produire."""
    decision: Decision
    motif: MotifModele | None = None
    reponse: str = Field(default="")
    citations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def coherence(self):
        if self.decision == "repondre":
            if self.motif is not None:
                raise ValueError("une réponse n'a pas de motif de refus")
            if not self.citations:
                raise ValueError("une réponse doit citer au moins un passage")
            if not self.reponse.strip():
                raise ValueError("réponse vide")
        else:
            if self.motif is None:
                raise ValueError("un refus doit avoir un motif")
        return self


def schema_json(etiquettes: list[str]) -> dict:
    """Schéma JSON passé à Ollama (paramètre format), avec l'énumération des étiquettes envoyées."""
    return {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["repondre", "refuser"]},
            "motif": {"anyOf": [{"type": "string", "enum": ["hors_corpus", "passages_insuffisants", "avis_juridique"]}, {"type": "null"}]},
            "reponse": {"type": "string"},
            "citations": {"type": "array", "items": {"type": "string", "enum": list(etiquettes)}},
        },
        "required": ["decision", "motif", "reponse", "citations"],
        "additionalProperties": False,
    }


class CitationAffichee(BaseModel):
    etiquette: str
    chunk_id: str
    source_titre: str
    identifiant: str
    reference: str  # « article 143, paragraphe 3 », « paragraphe 10 », « article 3, point 5 »
    texte: str  # texte exact du passage, issu de la base
    url: str
    version: str
    date_consultation: str
    contraignant: str  # « oui », « non » ou « statut non vérifié »


class ReponseAssistant(BaseModel):
    decision: Decision
    motif: MotifSysteme | None = None
    couche_refus: Literal["retrieval", "modele", "verification"] | None = None
    reponse: str = ""
    citations: list[CitationAffichee] = Field(default_factory=list)
    avertissement: str = AVERTISSEMENT
    controle_nombres: dict = Field(default_factory=dict)
    diagnostic: dict = Field(default_factory=dict)
