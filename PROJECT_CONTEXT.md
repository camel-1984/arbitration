# Project context: ML model for Russian bankruptcy auctions

## About the user and this project

- 3rd-year Software Engineering student at ITMO. Learning ML (has covered single decision trees; gradient boosting not yet covered in lectures).
- Final project for the ITMO ML course (mini coursework). The supervisor is nominal: no formal requirements, full freedom.
- Also intended as a portfolio project for an ML internship (target: December–February).
- Domain consultant and pilot user: the user's brother, a practicing arbitration manager (арбитражный управляющий).
- Communicate in Russian. The user directs and reviews, writes little code. Explain the reasoning behind decisions: the user must be able to defend every part of the project.
- Design follows Babushkin & Kravchenko "Machine Learning System Design" and the ml-system-design-doc template. Design doc: `docs/design.md` (Russian).

## Domain in short

When a person is declared bankrupt in Russia, their property is sold at open electronic auctions:

1. The arbitration manager values the property and sets the starting price. Currently done by hand, mostly by browsing Avito listings.
2. First auction (about 25 days of bid collection; with 2+ bids the auction is held) → repeated auction with starting price lowered by 10% → public offering (публичное предложение), where the price drops step by step on a schedule and the lot goes to the first valid bid at the current stage.
3. Auctions run on accredited electronic trading platforms (ЭТП). Announcements and results are published in ЕФРСБ (Fedresurs, bankrot.fedresurs.ru).

A wrong starting price is costly both ways: too high → the lot goes through repeated auction and public offering, months are lost; too low → creditors receive less and may challenge the valuation. Underpricing is partly self-correcting at a first auction with competition (price is bid up); overpricing is not.

## Decisions made (design doc section 1 and 2.1)

- **Single audience:** the arbitration manager. Buyers and creditors are out of scope (future work).
- **Asset scope:** passenger cars only (lots whose only ЦДТ category is 1 "Легковой транспорт"). Trucks, trailers, special machinery are postponed to the next version (brother asked for trucks: tell him they come second). Category 2 on ЦДТ mixes trucks, tractors, cranes; lots often have several categories.
- **Data:** sold passenger lots from ЭТП ЦДТ since 2024-01-01 (~15k lots; ~450–500 sold passenger lots per month), all of Russia. 2023 can be added later if validation shows lack of data. No external market prices (Avito, Kaggle listing datasets) in the main version; possible experiment later.
- **Object:** a sold lot with exactly one vehicle. Multi-vehicle lots are dropped.
- **Target:** log(final sale price, RUB). Not the manager's starting price (imitation was considered and rejected: it inherits managers' systematic errors).
- **Features:** vehicle characteristics (make, model, year, power, engine volume, mileage when present), condition flags from lot text (не на ходу, после ДТП, местонахождение неизвестно, no ПТС / keys), region, publication date. The starting price and anything from the results message (bids, winner, end date) are NOT features. Without the starting price the confounding problem (high start price ↔ better car) disappears from the model.
- **Task:** quantile regression, P25 / P50 / P75; loss: pinball loss.
- **Output for the manager:** quartiles stated as percentages ("25% of similar vehicles sell below 610k, 50% below 700k, 75% below 790k"); this is the expected sale price, NOT a recommended starting price (the manager chooses the start price, the forecast is a reference point), plus comparables (similar sold lots) and main factors (SHAP).
- **Offline metrics:** MdAPE of P50 in rubles; coverage of P25–P75 (should be about 50%); auxiliary tail metric: share of lots with P50 error > 50%; broken down by auction stage at which the lot was sold and by segments (age, price range).
- **Baseline:** median sale price of similar lots (same make/model, close year) sold earlier.
- **Pilot (business metric):** the brother first estimates the expected sale price blind (to avoid anchoring), then sees the model; after the lots are sold, compare whose estimate is closer to the actual sale price. Success = model error not worse than his. Feedback loop: his start price is set after seeing the forecast and public-offering prices follow the schedule from it → comparison biased toward the model; log blind estimate, forecast and chosen start price per lot, check competitive first-auction sales separately. Takes at least a month; few lots = first observations, not statistical proof.
- **Starting price recommendation is out of scope:** it is a causal question (what happens at price S); it needs unsold trades, whose failure reasons (price, procedure, winner refused) cannot be reliably separated, and the price effect is confounded with hidden condition.
- **P25–P75 coverage ≈ 50% is calibration, not success:** a useless model (global quartiles) also covers 50%; the corridor must also be narrower than the baseline's.
- **Manager's starting prices** are used only for analysis (how much they exceed actual sale prices), not as a target.
- **Planned experiment (after the first model):** a second model with the manager's Avito-based estimate as a FEATURE (not target): in training = start price of the first auction (requires linking auction stages of one lot), at inference = brother's own estimate recorded blind in the pilot. Compare with the main model (no start price). Captures the systematic discount to Avito and condition the manager saw in person; downside: depends on the manager's estimate quality.
- **Market context in UI:** links to Avito / Drom / Auto.ru searches built from make, model, year ±1 (no scraping, no prices pulled). Avito has no public listings API, so no listing cards. Rationale to explain: the model is trained on actual bankruptcy sale prices (market level is already inside the target via buyers), retrained regularly; weakness = lag after sharp market shocks, the market links are the manager's sanity check for that.

## Known limitations

- Selection bias: only sold lots have a sale price; unsold (likely worse) vehicles are missing → model is somewhat optimistic.
- Managers' decisions still leak into the target: at a first auction the sale price is not below the starting price (single bidder → sold at start price); on public offering the price follows the schedule derived from the starting price.
- Hidden vehicle condition not described in the lot text.
- Price drift after 2022 (sanctions, utilization fee): handled by the log target, a date feature and time-based validation.

## Known pitfalls (must be handled)

- **Leakage from the future:** for every feature ask whether it is known before the auction starts.
- **Same vehicle in train and test:** only sold trades are collected, so a car usually appears once; resales are found by VIN hash and removed. Time split handles the rest.
- **Time split**, not random split.
- **Comparables:** for a test lot, show only lots sold before it.
- **Rare makes / regions / vehicle types:** regularize, merge rare categories.
- **Dirty prices:** typos, thousands vs rubles → outlier cleaning.
- Use sklearn Pipeline / fit preprocessing on train only.

## Models and tooling (tentative)

- Baselines: median of comparables, linear regression on log price.
- Main model: CatBoost with quantile loss (categorical features natively).
- Lot text: regex extraction first (make, model, year, mileage, condition flags), then TF-IDF; later rubert-tiny2 embeddings.
- Explanations: SHAP. Comparables: kNN over features.
- Tooling: MLflow, FastAPI backend.
- Web UI: plain HTML/CSS/JS in `web/` (the user also needs it for a separate web course; requirements of that course unknown yet). Hybrid input: manager pastes the lot description → `/api/extract` prefills the form with our parser → manager checks/edits → `/api/predict` returns quartiles, factors, comparables. Form fields and flag definitions must match `docs/labeling_guide.md` exactly; make, model and year required (agreed: price without the model is meaningless), other fields optional ("не указано") to limit training-serving skew (power is present in ~18% of training texts; brother: many managers don't write power at all). Current `web/` is a skeleton with a demo fallback when the API is absent; local preview via `.claude/launch.json` (python http.server on 8000).

## Data collection plan (design doc 2.2)

- ЕФРСБ is protected by Qrator (403 even for a real automated browser); official API is paid. Not used, no bypass attempts.
- Main source: ЭТП ЦДТ (torgi.cdtrf.ru). Open JSON API without auth: `/api/Trade/trades?SignContract=true&Categories=1&PageSize=..&PageNum=..` (status flags by enumName: SignContract = sold with contract, Complete, NotHeld...; Categories: 1 passenger, 2 truck/commercial, 4 buses). Catalogs at `/api/Catalog/*`. robots.txt empty.
- Archive since Feb 2020; sold: 26,164 passenger, 4,680 truck/commercial (Oct 2026).
- List price is NOT final (equals start price). Lot card `/trades/{tradeId}` is HTML (SSR): description, start price, price-drop schedule with bid counts, final price ("Итоговая цена"), result date, protocols. Card data is taken from the Nuxt `__NUXT_DATA__` JSON embedded in the HTML; `/api/Trade/{id}` needs auth.
- Personal data at parse time: debtor and winner fields are not kept, debtor INN only as a hash (`debtor_key`); in lot texts VIN, plates, phones, names, INN and СНИЛС are masked; from VIN only WMI, the year code and a hash (`vin_hash`, for dedup) are kept. Date columns are parsed to datetime in the parser.
- Open: include company debtors or only individuals; other platforms (РАД) postponed.
- МЭТС (m-ets.ru) checked 2026-10-15 and dropped for now: car cards have structured fields (make, model, year, power, mileage, drive, gearbox) and final/contract price, but no API; robots.txt disallows everything except lot cards and sitemaps (search, catalog, pagination forbidden); sitemaps have no category → ~110k completed lots since 2024 to download for ~5% cars (~3k sold), ~24 h. Geo-blocks non-Russian IPs (needs split tunneling = user's real IP). Decision: work without МЭТС; do not bypass robots.txt. Revisit only if mileage proves critical (options: sample via sitemap, ask МЭТС for an export, user filters search manually).
- Related work: Жучкова С. (HSE, 2020), ranking of profitable car lots for buyers, manual feature extraction from text, platforms ЦДТ, МЭТС, НИС, РАД, Купецъ.

## Current status

- Design doc: sections 1, 2.1, 2.2, 2.3 written (short form), scope = passenger cars.
- Validation (2.3): split by publication date = `requestTimeBegin` (start of bid collection; also the collector's `--since` filter); drop lots published < 3 months before collection; expanding-window CV on 2024–2025 (4 folds, validate on each 2025 quarter); final model trained on 2024–2025, tested once on 2026; dedup by VIN hash (to add to parser); preprocessing fit on train fold only; baseline uses only earlier sales; learning curve to check data sufficiency.
- Collector `src/collect/cdtrf.py`: `--since 2024-01-01` required (catalog pages of 500, sorted by tradeId desc, NOT by date: dates are out of order by up to ~6 months, so after the first lot older than `--since` it scans 6 more pages). Polite: `--workers` parallel requests (3 tested: ~4.5k cards/h, no 429), 0.5–1 s delay per request, backoff 10/30/60/120 s on errors/429/5xx, failed ids to `data/raw/cdtrf/failed_cards.txt`, stops after 20 failures in a row; cards saved gzip-compressed and atomically; resumable (skips existing); `--max-minutes` (default 60) and `--limit` for portions; log `logs/collect_cdtrf.log`. Run portions of ~1 h with 30–60 min breaks under `caffeinate -i`. Parser reads `.html` and `.html.gz`.
- EDA: logic in `src/eda/` (load, summary, text_patterns, plots on seaborn), short notebook `notebooks/01_eda_sample.ipynb`. Do not print raw lot texts in notebooks (names may remain in free text).
- Sample of 100 passenger lots, 2022–2026: 76% sold on public offering, 24% auction; 50% sole participant; 99% individuals; sale price 10k–2.8M, median ~320k; year found in 77% of texts (97% with VIN year), VIN 85%, power 18%, mileage 2%, pledge 26%; regionID missing in 53% (mostly older lots); multi-vehicle passenger lots practically absent.
- Each auction stage is a separate trade; `lot_priceBegin` of a public offering is not the manager's original price. Linking stages (debtor_key + text) needed for group split.
- Gold set for text extraction: `labels/gold.csv` (tracked, no texts; 127 lots, dev 52 by the user, test 75 by Claude). Labeling flow: prelabel csv (tradeId, make, model, year, exclude, comment; prelabeled by Claude from text only) → `src/labels/make_gold_template.py <prelabel.csv>` builds `data/labels/gold_to_fill.xlsx` (local, with texts) where the user fills condition flags (major_defect = serious mechanical defect incl. "на ходу, но капремонт"; damaged; no_keys_or_docs; pledge; arrest_or_ban; location_unknown), power_hp, engine_cc and checks make/model/year. Rules: `docs/labeling_guide.md`. Parser now also masks names (patronymic and initials patterns), plates with slash; masking is still imperfect, texts stay local.
- LLM extraction plan: compare regex vs LLM (Claude Haiku 5.5, thinking off, low effort, Batch API for the full run, ~$2–5 for 26k lots) on the gold set; API key needed (subscription does not cover API).
- Collection done (2026-10-15): 15,005 cards, 0 errors, ~5 h total (3 workers ~4.5k cards/h). Processed: 14,919 lots (sold, one VIN), 14,909 published since 2024-01-01 (~1.1-1.75k per quarter; 2026Q3 incomplete, 2026Q4 = 3).
- EDA on full data started (2026-10-15, notebook `02_eda.ipynb` not written yet). Preliminary findings (14,909 lots since 2024-01-01):
  - sale price: median 333k, 1% 16k, 99% 2.8M, max 522M (typos); sale/start ratio > 3 in 90 lots, < 0.1 in 19; 207 lots below 20k.
  - stages: public offering 68% (median sale/start-of-stage 0.72), auction 32% (median 1.00); sole participant 48%.
  - VIN duplicates: 453 groups (934 lots), same debtor, median gap 97 days, relisted after the previous contract in 81%, earlier price higher in 86% → failed contract and relisting; keep the last sale per VIN.
  - lots selling a share of a car (1/2 доли): 28 → drop.
  - coverage: make/model 94%, year 95.5% (text), VIN year code 85%, power 12%, engine 12%, region 48%; flags: pledge 27%, major_defect 5%, damaged 4.7%, arrest 2.9%, no_keys 0.5%, location_unknown 0 (regex finds nothing on full data: check).
  - 43 makes, 1,673 make+model combos, 117 with >= 20 lots cover 68% of lots, 858 singletons (model normalization matters).
  - age: median 14 years; log price vs age corr -0.62, slope ≈ -0.098 per year (~-9% per year).
  - median price ratio with/without flag: major_defect 0.49, damaged 0.60; pledge 1.72 and arrest 1.25 (confounded: pledged cars are newer/credit cars).
  - quarterly median price flat ~300-360k, no strong drift; 908 lots published after 2026-07-15 (to drop by the 3-month rule).
- Next: EDA on full data (`02_eda.ipynb`: price outliers, VIN duplicates, feature coverage, price by month and stage) → cleaning rules in `src/dataset/build.py` → regex fixes on dev (model normalization, power formats, year from VIN code) → label ~75 fresh lots as `test2` → optional LLM extraction comparison on the gold set → baseline + time CV → linear → CatBoost.

