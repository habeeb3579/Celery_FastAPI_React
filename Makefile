# ══════════════════════════════════════════════════════════════
# ML Project — Makefile
# Usage: make <target>
# ══════════════════════════════════════════════════════════════

PYTHON    = python
SCRIPT    = tests/run_experiment.py
DATASET   = iris
MODEL     = random_forest
ENV_NAME  = ml_experiment_env
CONDA_RUN = conda run -n $(ENV_NAME)

DC = docker compose

.PHONY: help \
        up up-monitoring up-dev down stop restart rebuild logs \
        ps clean volumes-rm \
        env-create env-delete env-clean \
        run custom compare benchmark save

# ── Help ───────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  ── Docker ────────────────────────────────────────────"
	@echo "    up              Start core services (api, workers, redis)"
	@echo "    up-monitoring   Start core + Flower + Redis Commander"
	@echo "    up-dev          Start everything (+ Jupyter + Frontend)"
	@echo "    down            Stop and remove containers"
	@echo "    stop            Stop containers without removing"
	@echo "    restart         Restart all running containers"
	@echo "    rebuild         Rebuild images and restart"
	@echo "    logs            Tail logs for all running services"
	@echo "    ps              Show running containers"
	@echo "    clean           Remove containers, images, orphans"
	@echo "    volumes-rm      Remove all volumes (wipes Redis data)"
	@echo ""
	@echo "  ── Conda Environment ─────────────────────────────────"
	@echo "    env-create      Create conda env and install deps"
	@echo "    env-delete      Delete the conda environment"
	@echo "    env-clean       Remove __pycache__ and results.json"
	@echo ""
	@echo "  ── Experiments ───────────────────────────────────────"
	@echo "    run             Single run — iris + random_forest"
	@echo "    custom          Custom — override with DATASET= MODEL="
	@echo "    compare         All models on breast_cancer"
	@echo "    benchmark       Full 16-combination benchmark"
	@echo "    save            digits + svm, save to results.json"
	@echo ""
	@echo "  ── Examples ──────────────────────────────────────────"
	@echo "    make up-dev"
	@echo "    make custom DATASET=wine MODEL=gradient_boosting"
	@echo "    make logs"
	@echo "    make down volumes-rm"
	@echo ""

# ── Docker — profiles ──────────────────────────────────────────

up:
	$(DC) --profile core up -d

up-monitoring:
	$(DC) --profile monitoring up -d

up-dev:
	$(DC) --profile dev up -d

# ── Docker — lifecycle ─────────────────────────────────────────

down:
	$(DC) --profile dev --profile monitoring --profile core down

stop:
	$(DC) --profile dev --profile monitoring --profile core stop

restart:
	$(DC) --profile dev --profile monitoring --profile core restart

rebuild:
	$(DC) --profile dev --profile monitoring --profile core down
	$(DC) --profile dev build --no-cache
	$(DC) --profile dev up -d

logs:
	$(DC) --profile dev --profile monitoring --profile core logs -f

ps:
	$(DC) ps

# ── Docker — cleanup ───────────────────────────────────────────

clean:
	$(DC) --profile dev --profile monitoring --profile core down \
		--rmi local --remove-orphans

volumes-rm:
	$(DC) --profile dev --profile monitoring --profile core down -v
	@echo "  Warning: Redis data and all volumes have been deleted."

# ── Conda Environment ──────────────────────────────────────────

env-create:
	@echo "Creating conda environment: $(ENV_NAME)..."
	conda create -n $(ENV_NAME) python=3.11 -y
	conda run -n $(ENV_NAME) pip install httpx rich typer scikit-learn numpy
	@echo "  Done. Activate with: conda activate $(ENV_NAME)"

env-delete:
	@echo "Deleting conda environment: $(ENV_NAME)..."
	conda env remove -n $(ENV_NAME) -y
	@echo "  Done."

env-clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f results.json
	@echo "  Done."

# ── Experiments ────────────────────────────────────────────────

run:
	$(CONDA_RUN) $(PYTHON) $(SCRIPT) run

custom:
	$(CONDA_RUN) $(PYTHON) $(SCRIPT) run --dataset $(DATASET) --model $(MODEL)

compare:
	$(CONDA_RUN) $(PYTHON) $(SCRIPT) compare --dataset breast_cancer

benchmark:
	$(CONDA_RUN) $(PYTHON) $(SCRIPT) all

save:
	$(CONDA_RUN) $(PYTHON) $(SCRIPT) run --dataset digits --model svm --save