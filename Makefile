# Commandes du projet. Prérequis : voir README.md (uv, Node, Ollama, poppler).
# Rien ici ne publie ni ne pousse quoi que ce soit.

PY = backend/.venv/bin/python

.PHONY: setup modeles telecharger verifier ingest serve front test eval-dev

setup:  ## Dépendances Python (uv) et Node. Ne télécharge aucun modèle.
	cd backend && uv sync
	cd frontend && npm install

modeles:  ## Télécharge les deux modèles Ollama (environ 7,8 Go au total). À lancer en connaissance de cause.
	ollama pull bge-m3
	ollama pull qwen3.5:9b

telecharger:  ## Télécharge les textes du registre qui ont une URL (EUR-Lex, EBA, AMF). L'ordonnance et les Q&A ESMA sont manuelles.
	$(PY) scripts/telecharger.py

verifier:  ## Compare les hash des textes dans data/raw avec data/sources.yaml
	$(PY) scripts/telecharger.py --verifier

ingest:  ## Découpe les textes en passages : data/processed/chunks.jsonl
	cd backend && .venv/bin/python -m app.chunking.construire

serve:  ## API locale sur http://localhost:8000
	cd backend && .venv/bin/uvicorn app.api.main:app --port 8000

front:  ## Interface sur http://localhost:3000 (lancer `make serve` avant)
	cd frontend && npm run dev

test:  ## Tests Python (certains exigent Ollama avec bge-m3 et les textes dans data/raw)
	cd backend && .venv/bin/pytest -q
	cd frontend && npm run typecheck

eval-dev:  ## Mesure sur les questions de développement. Le test figé exige --confirmer-test (voir eval/).
	$(PY) eval/run_retrieval.py
	$(PY) eval/run_generation.py --modele qwen3.5:9b
