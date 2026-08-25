# Requires `make` (not installed by default on Windows -- via choco/scoop/
# WSL, or just run the commands below directly; every target here is a
# thin wrapper around a single `python scripts/...` call, nothing make-
# specific happens inside them).
#
# Run from the repo root. All Python commands execute with backend/ as the
# working directory, matching how the app itself runs (imports are flat,
# e.g. `from services.scoring import ...`, not package-qualified).

PYTHON := backend/venv/Scripts/python.exe

.PHONY: eval eval-legacy eval-dual test

eval: eval-legacy eval-dual

# Evaluates the LIVE route's pipeline (legacy_ats_score -> full_analysis)
# against the 39-resume human-labeled corpus.
eval-legacy:
	cd backend && $(PYTHON) scripts/resume_eval_predict.py
	cd backend && $(PYTHON) scripts/resume_eval_report.py

# Evaluates the Phase 0 dual-mode pipeline (services.analysis) in both
# quality and match mode, against the same corpus.
eval-dual:
	cd backend && $(PYTHON) scripts/resume_eval_dual_mode.py

test:
	cd backend && $(PYTHON) -m pytest -q
