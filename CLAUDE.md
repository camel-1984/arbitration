@PROJECT_CONTEXT.md

# Working conventions

- ML course project: Mode 1 (teacher). The user directs and reviews; explain decisions so the user can defend them.
- Design doc `docs/design.md` follows the Babushkin ml-system-design-doc template, written in Russian in report style (no em dashes, plain paragraphs). Read it before continuing design work.
- Keep `docs/design.md` short for now (key decisions only, a few lines per section). A detailed version for the defense is written at the end of the project.
- Discuss a section in chat first; write it to `docs/design.md` only after the user agrees.
- Keep `PROJECT_CONTEXT.md` "Decisions made" and "Current status" up to date when decisions change.
- Model ladder agreed: median of comparables → linear regression on log price (SimpleImputer with missing indicator, one-hot with regularization) → CatBoost MultiQuantile. Final choice by validation, not in advance.

# Layout

- `src/collect/` download raw data, `src/parse/` raw → `data/interim/`, `src/features/` feature extraction, `src/dataset/` interim → `data/processed/`, `src/labels/` gold set tools, `src/eda/` EDA helpers called from `notebooks/`.
- `labels/` tracked labels without texts, `docs/` design doc and labeling guide, `web/` UI (HTML/CSS/JS).

# Commands (run from repo root, always as modules: `python -m src.<package>.<module>`)

- `caffeinate -i .venv/bin/python -m src.collect.cdtrf --since 2024-01-01 --max-minutes 60` - one collection portion (3 workers by default, ~4.5k cards/h); run in background; log `logs/collect_cdtrf.log`; resumable.
- `.venv/bin/python -m src.parse.cdtrf` - raw cards (`.html`/`.html.gz`) → `data/interim/cdtrf_cards.parquet`.
- `.venv/bin/python -m src.dataset.build` - interim cards + text features → `data/processed/lots.parquet` (drops unsold and multi-VIN lots, adds `log_price`; cleaning rules go here).
- `.venv/bin/python -m src.labels.evaluate_extraction --split dev|test|all|<name>` - regex extraction vs gold set.
- `.venv/bin/python -m src.labels.make_gold_template <prelabel.csv>` - build `data/labels/gold_to_fill.xlsx` for the lots in the prelabel csv, keeps filled labels (user must close Excel first); `-m src.labels.export_gold --split <name> --annotator human|claude` appends new lots from it to `labels/gold.csv` (existing tradeIds untouched). `labels/gold.csv` is the only source of gold labels; texts are joined from the parquet.
- `.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/<name>.ipynb` - execute notebook after edits.
- Web preview: launch config `web` in `.claude/launch.json` (http.server on 8000, `--directory web`); opening `web/index.html` directly loads as data: URL without `app.js`.

# Gotchas

- venv is Python 3.14; after `pip install` add the pinned version to `requirements.txt`.
- Gold `test` split was labeled by Claude (`annotator` column); do not tune regex on it. After regex changes, measure on newly labeled lots.
- Never print raw lot texts in notebooks or committed files: masking misses some names. `data/`, `logs/`, `misc/` are gitignored; `CLAUDE.md` and `PROJECT_CONTEXT.md` are tracked, so keep personal data out of them.
- ЕФРСБ is behind Qrator: do not retry. The built-in browser is outside Russia (auto.ru shows a region notice; do not accept it).
- Web UI: the user rejected the frontend-design restyle; keep the plain skeleton style unless asked.
