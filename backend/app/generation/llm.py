"""Appel au modèle de génération via Ollama, derrière une interface minimale pour pouvoir tester avec un faux modèle."""
import json
import urllib.request
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ResultatLLM:
    content: str
    done_reason: str
    prompt_eval_count: int
    eval_count: int
    num_ctx: int
    modele: str


class LLM(Protocol):
    def chat(self, messages: list[dict], schema: dict) -> ResultatLLM: ...


class OllamaLLM:
    """Paramètres choisis pour la reproductibilité : température 0, graine fixe, réflexion désactivée,
    contexte explicite (Ollama ne signale pas une troncature du prompt dans la documentation consultée),
    sortie contrainte par le schéma JSON (paramètre format)."""

    def __init__(self, modele: str, num_ctx: int = 16384, seed: int = 7, num_predict: int = 800,
                 url: str = "http://localhost:11434", delai: int = 900):
        self.modele, self.num_ctx, self.seed, self.num_predict, self.url, self.delai = modele, num_ctx, seed, num_predict, url, delai

    def chat(self, messages: list[dict], schema: dict) -> ResultatLLM:
        corps = {
            "model": self.modele, "messages": messages, "stream": False, "think": False, "format": schema,
            "keep_alive": "10m",
            "options": {"temperature": 0, "seed": self.seed, "num_ctx": self.num_ctx, "num_predict": self.num_predict,
                        "top_k": 1, "presence_penalty": 0},  # presence_penalty : non documenté pour /api/chat, effet non vérifié
        }
        requete = urllib.request.Request(f"{self.url}/api/chat", data=json.dumps(corps).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(requete, timeout=self.delai) as r:
            d = json.load(r)
        return ResultatLLM(
            content=d.get("message", {}).get("content", ""), done_reason=d.get("done_reason", ""),
            prompt_eval_count=int(d.get("prompt_eval_count", 0)), eval_count=int(d.get("eval_count", 0)),
            num_ctx=self.num_ctx, modele=self.modele,
        )
