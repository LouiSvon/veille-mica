"""API locale de l'assistant de veille réglementaire.

Lancement : cd backend && uv run uvicorn app.api.main:app --port 8000
Tout fonctionne en local (Ollama). Chaque réponse porte l'avertissement « Ceci n'est pas un conseil juridique. ».
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from app.generation.llm import LLM, OllamaLLM
from app.generation.pipeline import Config, repondre
from app.generation.schema import AVERTISSEMENT, ReponseAssistant
from app.retrieval.dense import embedder_ollama
from app.retrieval.retriever import Retriever

RACINE = Path(__file__).resolve().parents[3]
MODELE_PAR_DEFAUT = "qwen3.5:9b"
ORIGINES_AUTORISEES = ["http://localhost:3000", "http://127.0.0.1:3000"]


journal = logging.getLogger("veille")
DIAGNOSTIC_INTERNE = ("reponse_rejetee", "erreurs_format")  # jamais renvoyés au client : texte du modèle non vérifié


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1000)

    @field_validator("question", mode="before")
    @classmethod
    def sans_espaces_autour(cls, v):
        # Le contrôle de longueur doit porter sur la question réelle, pas sur des espaces.
        return v.strip() if isinstance(v, str) else v


class Etat(BaseModel):
    statut: str
    avertissement: str = AVERTISSEMENT
    modele: str
    mode_recherche: str
    nombre_passages: int
    sources: list[dict]


def creer_app(retriever=None, llm: LLM | None = None, config: Config | None = None) -> FastAPI:
    """Fabrique de l'application. Les tests injectent un faux retriever et un faux modèle ;
    sans argument, les composants réels sont chargés au démarrage."""
    contexte: dict = {"retriever": retriever, "llm": llm, "config": config or Config()}

    @asynccontextmanager
    async def cycle_de_vie(_app):
        if contexte["retriever"] is None:
            contexte["retriever"] = Retriever.depuis_fichier(
                RACINE / "data" / "processed" / "chunks.jsonl", embedder=embedder_ollama(),
                cache=RACINE / "data" / "processed" / "embeddings.npz", nom_modele="bge-m3")
        if contexte["llm"] is None:
            contexte["llm"] = OllamaLLM(os.environ.get("VEILLE_MODELE", MODELE_PAR_DEFAUT))
        yield

    app = FastAPI(title="Veille réglementaire crypto-actifs", version="0.1.0", lifespan=cycle_de_vie,
                  description=AVERTISSEMENT + " Assistant de recherche dans des textes officiels, sans avis juridique.")
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINES_AUTORISEES, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.exception_handler(RequestValidationError)
    async def entree_invalide(_req: Request, _exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": "Question invalide : 3 à 1000 caractères.", "avertissement": AVERTISSEMENT})

    @app.exception_handler(Exception)
    async def erreur_interne(_req: Request, exc: Exception):
        journal.error("erreur interne : %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Erreur interne.", "avertissement": AVERTISSEMENT})

    @app.get("/health", response_model=Etat)
    def sante() -> Etat:
        passages = contexte["retriever"].passages
        sources = {}
        for p in passages:
            s = sources.setdefault(p["source"], {"source": p["source"], "titre": p["source_titre"], "version": p["version"],
                                                 "date_consultation": p["date_consultation"], "passages": 0})
            s["passages"] += 1
        return Etat(statut="ok", modele=getattr(contexte["llm"], "modele", "inconnu"), mode_recherche=contexte["config"].mode,
                    nombre_passages=len(passages), sources=list(sources.values()))

    @app.post("/ask", response_model=ReponseAssistant)
    def demander(corps: Question) -> ReponseAssistant:
        r = repondre(corps.question, contexte["retriever"], contexte["llm"], contexte["config"])
        for cle in DIAGNOSTIC_INTERNE:
            texte = r.diagnostic.pop(cle, None)
            if texte:
                journal.info("diagnostic %s écarté de la réponse (%d caractères)", cle, len(str(texte)))
        return r

    return app


app = creer_app()
