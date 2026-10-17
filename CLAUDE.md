@PROJECT_CONTEXT.md

# Working conventions

- ML course project: Mode 1 (teacher). The user directs and reviews; explain decisions so the user can defend them.
- Design doc `docs/design.md` follows the Babushkin ml-system-design-doc template, written in Russian in report style (no em dashes, plain paragraphs). Read it before continuing design work.
- Keep `docs/design.md` short for now (key decisions only, a few lines per section). A detailed version for the defense is written at the end of the project.
- Discuss a section in chat first; write it to `docs/design.md` only after the user agrees.
- Keep `PROJECT_CONTEXT.md` "Decisions made" and "Current state" up to date when decisions change; "Current state" is a snapshot, not a log (experiment history lives in `journal/`).
- Experiments are logged in `journal/` (Probabl Skills, light variant): `JOURNAL.md` index + `NN_name.md` design note per experiment; write the note and get explicit user approval before code, record the outcome in the note and the History row afterwards.
- Model ladder: median of comparables → linear quantile regression on log price → CatBoost MultiQuantile → current: ensemble linear + CatBoost 50/50 in log space (`src/models/ensemble.py`) in two modes, without the start price and with the first-auction start price (`with_start=True`). Choices by validation, not in advance. Planned (main line, design doc 2.1): model 2 typical first-auction start price (B14), model 3 P(sold at the first auction | start) (B10).

# Layout

- `src/collect/` download raw data, `src/parse/` raw → `data/interim/`, `src/features/` feature extraction, `src/dataset/` interim → `data/processed/`, `src/labels/` gold set tools, `src/eda/` EDA helpers called from `notebooks/`, `src/models/` time CV + metrics (`evaluate.py`), models (`baseline.py`, `linear.py`, `catboost_model.py`, `ensemble.py`; each `predict(train, valid[, with_start]) -> DataFrame[p25, p50, p75]`), `comparables.py` (similar sold lots), `explain.py` (factors in % from the linear model). `typical_start.py` model 2: the same ensemble on the target log(first-auction start) over all first auctions (`target_lots(read_first())`), own `WIDTH_K`. `first_sale.py` model 3: P(sold at the first auction) on `data/processed/first_auctions.parquet`, logistic + CatBoost (monotone in `PRICE`), market features from the model 1 ensemble (`market_quantiles`, `with_market`: start / P50 ratio and P75-P25 width, OOF by debtor in train; one CV ≈ 15 min), `price_curve(models, lot, market_log_q, prices)` for the UI scale; its folds also require the first auction to have ended before the quarter (`outcome_at`).
- `src/features/normalize.py` make/model normalization (phonetic key, VIN WMI+VDS, `labels/model_aliases.csv`); `src/dataset/stages.py` first-auction price by linking auction stages; `src/parse/cdtrf_list.py` all-status catalog; `src/dataset/web_catalog.py` selects for the web form.
- `labels/` tracked labels without texts, `docs/` design doc and labeling guide, `web/` UI (HTML/CSS/JS).

# Commands (run from repo root, always as modules: `python -m src.<package>.<module>`)

- `caffeinate -i .venv/bin/python -m src.collect.cdtrf --since 2023-01-01 --max-minutes 60` - one collection portion (3 workers by default, ~4.5k cards/h); run in background; log `logs/collect_cdtrf.log`; resumable.
- `.venv/bin/python -m src.collect.cdtrf --since 2022-01-01 --list-all` - only catalog pages of all trade statuses (~144 pages, ~35 min), for stage linking; `-m src.parse.cdtrf_list` → `data/interim/cdtrf_trades.parquet` (used by `build` if present).
- `caffeinate -i .venv/bin/python -m src.collect.cdtrf --ids data/interim/first_auction_ids.txt --cards-dir data/raw/cdtrf/cards_first --limit 30000 --max-minutes 60` - cards of first auctions with any outcome for model 3 (ids from `stages.first_auctions`), resumable.
- `.venv/bin/python -m src.parse.cdtrf` - raw cards (`.html`/`.html.gz`) → `data/interim/cdtrf_cards.parquet`.
- `.venv/bin/python -m src.dataset.build` - interim cards + text features → `data/processed/lots.parquet` (drops unsold and multi-VIN lots, fills year from VIN for WMIs with ≥95% agreement, applies cleaning rules and prints how many lots each removed, normalizes make/model (`src/features/normalize.py`), fills region from the court code, adds `log_price`).
- `.venv/bin/python -m src.models.baseline` / `-m src.models.linear [--tune]` / `-m src.models.catboost_model [--tune]` / `-m src.models.ensemble [--with-start]` (current best; `--with-start` adds the first-auction start price) - time CV on 2025 quarters (expanding window), prints per-fold metrics and breakdowns; `--tune` grid-searches hyperparameters (slow, run in background).
- `.venv/bin/python -m src.labels.evaluate_extraction --split dev2|flags|test2|all|<name> [--extractor regex|llm]` - extraction vs gold set; `llm` needs `ollama serve` running (model `qwen3:8b`), answers cached in `data/interim/llm_cache.jsonl`.
- `.venv/bin/python -m src.labels.make_gold_template <prelabel.csv>` - build `data/labels/gold_to_fill.xlsx` for the lots in the prelabel csv, keeps filled labels (user must close Excel first); `-m src.labels.export_gold --split <name> --annotator human|claude` appends new lots from it to `labels/gold.csv` (existing tradeIds untouched). `labels/gold.csv` is the only source of gold labels; texts are joined from the parquet.
- Claude labeling flow: sample ids to `data/labels/<split>_ids.csv` (fixed `random_state`, exclude all gold tradeIds), read texts in batches of 50 (title + info from interim parquet), write `data/labels/<split>_labels.csv` with gold columns (empty = 0/unknown; quote comments containing commas), then append to `labels/gold.csv` with `split`, `annotator=claude` after asserting no tradeId overlap. Label from text only, never look at extractor output first.
- `.venv/bin/jupyter nbconvert --to notebook --execute --inplace notebooks/<name>.ipynb` - execute notebook after edits.
- `.venv/bin/python -m src.dataset.web_catalog` - makes, models (≥3 lots) and region names → `web/catalog.json` for the form selects; rerun after rebuilding the dataset.
- Web preview: launch config `web` in `.claude/launch.json` (http.server on 8000, `--directory web`); opening `web/index.html` directly loads as data: URL without `app.js`.
- `PYTHONPATH=. .venv/bin/python -m uvicorn src.api.app:app --port 8001` - FastAPI (`src/api/app.py`): serves `web/`, `/api/extract` (regex), pilot journal `/api/pilot` in `data/pilot/journal.json`; `/api/predict` is 501 until models are saved. The launch config `app` hangs (the preview helper never starts the venv python): run uvicorn via Bash in background and open `preview_start` with `url: http://localhost:8001`.

# Gotchas

- venv is Python 3.14; after `pip install` add the pinned version to `requirements.txt`.
- Ad-hoc scripts outside the repo root: `PYTHONPATH=. .venv/bin/python <path>/script.py` (run from repo root), otherwise `import src...` fails.
- Patching models in experiments: `linear.make_model` binds `ALPHA` / `MIN_FREQUENCY` as default args at import, so pass them via `functools.partial(linear.make_model, alpha=..., min_frequency=...)`; `catboost_model.features` selects columns by the module-level `CATEGORICAL` / `NUMERIC` lists at call time, so changing them changes the feature set.
- CatBoost CTR `Borders:TargetBorderCount=15` is for regression only; a CatBoostClassifier (Logloss) must use default CTR.
- Timing on 2023+ data: one ensemble CV ≈ 1.5-2 min per mode, `--with-start` slower (OOF market model); grids and multi-variant scripts take 10-40 min: run them in background with output to a file.
- If `preview_start` with config `web` fails because port 8000 is busy (another session's server), open it with `preview_start` + `url: http://localhost:8000`; `curl` to localhost does not work from the Bash sandbox.
- `lot_regionID` = federal subject code (77 Moscow, 66 Sverdlovsk); the court code in `dealNum` («А40») maps to it, see `add_region` in `build.py`.
- Gold splits: tune regex only on `dev2` and `flags`; `dev`/`test` are overfit; `test2` was used for the regex vs Qwen comparison (gold values seen) - any further extractor tuning needs a new holdout.
- Lots published from 2026-01-01 are the final test set: never use them in CV or tuning. CV folds = 2025 quarters.
- Sale stage (auction / public offering) and result fields are never features; stage is only for breakdowns or as a target of auxiliary models. The start price of the stage at which the lot sold is not a feature; only the FIRST-auction start price (`first_price`) is, and only in the `with_start` model.
- Honest CV: a fold trains only on lots sold before the quarter start (`sold_at` in `evaluate.py`); any new split or calibration must respect it.
- After changing a model, recompute the corridor coefficients `WIDTH_K` in `ensemble.py` (sequential scheme, journal 12); after rebuilding the dataset, rerun `src.dataset.web_catalog`.
- Scratch experiment scripts and outputs go to `misc/scratch_<date>/` (gitignored); the journal note cites them.
- Git history was squashed on 2026-10-16 and 2026-10-17 to 5 commits (old history: branch `backup/before-squash`, tags `backup-before-squash-2`, `backup-before-squash-3`): commit on top of main, never reset to a backup. The journal lives only in `journal/`.
- Ollama is not autostarted: run `ollama serve` in background first. qwen3:8b ≈ 13 s/lot on the M3 (memory-bandwidth bound); CPU-heavy jobs in parallel (CV, tuning) slow both down.
- `data/processed/lots.parquet` is post-cleaning (no VIN relistings, no censored months, no typos). EDA of raw data issues uses `src.eda.load.load_lots()`, which rebuilds pre-clean lots from the interim cards via `src.dataset.build.prepare`.
- Never print raw lot texts in notebooks or committed files: masking misses some names. `data/`, `logs/`, `misc/` are gitignored; `CLAUDE.md` and `PROJECT_CONTEXT.md` are tracked, so keep personal data out of them.
- ЕФРСБ is behind Qrator: do not retry. The built-in browser is outside Russia (auto.ru shows a region notice; do not accept it).
- Web UI (2026-10-16, impeccable skill): one light theme from the hero video `web/media/amg.mp4` (concrete, graphite, amber), fonts Tektur + Onest, no theme toggle; keep this direction. Numbers are typed text fields (the user rejected sliders and spinners), empty = "не указано"; make / model / region are selects from `catalog.json`. The browser caches `style.css` / `app.js`: refetch with `cache: 'reload'` when checking changes. Result screen (2026-10-17) follows the three models: 6 typical start + price ladder with P(sold at the first auction), 7 two outcomes and the sale corridor for the chosen price, 8 collapsed basis (market without start, factors, comparables, links); contract in `docs/api.md`, demo data in `demoPrediction`. The Tektur subset has no `%` glyph: render percent signs in Onest (`.pct`). Two modes via the top switch (`body[data-mode]`, `.prepare-only` / `.check-only`): «До выставления» (text or manual input, start price step, blind estimate, pilot journal) and «Уже на торгах» (ЦДТ link only, start price from the card, auto-evaluates, no journal); step numbers are renumbered in JS.

## Agent skills

### Issue tracker

Local markdown: issues and specs live as files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `GLOSSARY.md` + `docs/adr/` (created lazily); existing decisions live in `docs/design.md`, `PROJECT_CONTEXT.md` and `journal/`. See `docs/agents/domain.md`.
