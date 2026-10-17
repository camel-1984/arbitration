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

Manager's goal (the brother, 2026-10-17): the best outcome is a sale at the first auction - the price is higher, the fee (a percentage of the proceeds) is higher, and the procedure can be closed sooner. So the start price is a trade-off: high enough for the proceeds and to withstand challenges as market value, low enough for a buyer to appear at the first auction. In the data (13.5k lots with a linked first start) 48% sell at an auction (44% of them exactly at the start, i.e. a single bidder, 38% bid up, 16% at the repeated auction), 52% go to public offering at a median 0.64 of the first start.

A wrong starting price is costly both ways: too high → the lot goes through repeated auction and public offering, months are lost; too low → creditors receive less and may challenge the valuation. Underpricing is partly self-correcting at a first auction with competition (price is bid up); overpricing is not.

## Decisions made (design doc section 1 and 2.1)

- **Single audience:** the arbitration manager. Buyers and creditors are out of scope (future work).
- **Asset scope:** passenger cars only (lots whose only ЦДТ category is 1 "Легковой транспорт"). Trucks, trailers, special machinery are postponed to the next version (brother asked for trucks: tell him they come second). Category 2 on ЦДТ mixes trucks, tractors, cranes; lots often have several categories.
- **Data:** sold passenger lots from ЭТП ЦДТ since 2023-01-01 (17.7k lots after cleaning; 2023 added 2026-10-16 with the spline trend, journal 20), all of Russia. No external market prices (Avito, Kaggle listing datasets) in the main version; possible experiment later.
- **Object:** a sold lot with exactly one vehicle. Multi-vehicle lots are dropped.
- **Target:** log(final sale price, RUB). Not the manager's starting price (imitation was considered and rejected: it inherits managers' systematic errors).
- **Features:** vehicle characteristics (make, model, year, power, engine volume, mileage when present), condition flags from lot text (не на ходу, после ДТП, местонахождение неизвестно, no ПТС / keys), region, publication date. Anything from the results message (bids, winner, end date) is NOT a feature.
- **Two models (decided 2026-10-16, journal 08, 13):** the main model has no starting price (independent reference); the second one adds the start price of the FIRST auction (the manager's valuation) as a feature and is used when the manager fills the optional form field "planned start price of the first auction". Target stays the actual sale price, so the second model learns the auction discount to the valuation, not the valuation itself. One model with an optional (masked) start feature was worse in both modes.
- **Task:** quantile regression, P25 / P50 / P75; loss: pinball loss.
- **Product direction (decided 2026-10-17, main line of work):** three models with shared features and validation. (1) Sale price (done): quartiles P25/P50/P75 of the actual sale price, two modes. (2) Typical start price (backlog B14): what other managers set as the first-auction start for such a car; target log(first start) on ~13.5k linked lots; here imitating managers is the goal (by law the start is market value, practice is its defensible estimate). (3) Sale at the first auction (B10): P(sold at the first auction | car, start price) from the all-status catalog; monotone decreasing in price, calibrated (log loss, Brier, reliability curve, AUC). UI hierarchy: top - a scale of start prices around the typical one with P(sold immediately) and the manager's price marked; then two scenarios for the chosen price (sold at the first auction not below the start with p, or public offering with the price corridor of model 1); collapsed below - comparables, factors, market links.
- **Output for the manager:** model 1 quartiles stated as percentages ("25% of similar vehicles sell below 610k, 50% below 700k, 75% below 790k"); no single "recommended" start price: the manager chooses, the typical start and P(sold immediately) are reference points.
- **Offline metrics:** MdAPE of P50 in rubles; coverage of P25–P75 (should be about 50%); auxiliary tail metric: share of lots with P50 error > 50%; broken down by auction stage at which the lot was sold and by segments (age, price range).
- **Baseline:** median sale price of similar lots (same make/model, close year) sold earlier.
- **Pilot (business metric):** the brother first estimates the expected sale price blind (to avoid anchoring), then sees the model; after the lots are sold, compare whose estimate is closer to the actual sale price. Success = model error not worse than his. Feedback loop: his start price is set after seeing the forecast and public-offering prices follow the schedule from it → comparison biased toward the model; log blind estimate, forecast and chosen start price per lot, check competitive first-auction sales separately. Takes at least a month; few lots = first observations, not statistical proof.
- **Optimal starting price is out of scope:** it is a causal question (what happens at price S); failure reasons of unsold trades (price, procedure, winner refused) cannot be reliably separated, and the price effect is confounded with hidden condition (cheaper starts go to worse cars). Models 2 and 3 are predictive and worded as "similar lots at this price sold immediately in X%", never "lower the price and it will sell".
- **P25–P75 coverage ≈ 50% is calibration, not success:** a useless model (global quartiles) also covers 50%; the corridor must also be narrower than the baseline's.
- **Manager's starting prices** are used only for analysis (how much they exceed actual sale prices), not as a target.
- **Second model details:** in training the first-auction start price comes from linking auction stages via the all-status catalog (fallback: public offering start / 0.9); at inference it is the manager's planned start price (in the pilot: recorded blind). Downside: depends on the manager's estimate quality; weak on lots sold at the first auction (bimodal price).
- **Market context in UI:** links to Avito / Drom / Auto.ru searches built from make, model, year ±1 (no scraping, no prices pulled). Avito has no public listings API, so no listing cards. Rationale to explain: the model is trained on actual bankruptcy sale prices (market level is already inside the target via buyers), retrained regularly; weakness = lag after sharp market shocks, the market links are the manager's sanity check for that.

## Known limitations

- Selection bias: only sold lots have a sale price; unsold (likely worse) vehicles are missing → model is somewhat optimistic.
- Managers' decisions still leak into the target: at a first auction the sale price is not below the starting price (single bidder → sold at start price); on public offering the price follows the schedule derived from the starting price.
- Hidden vehicle condition not described in the lot text.
- Expensive and rare cars are underpredicted: the model compresses the price scale toward the mean (2026 test: P50 1.5-3 mln is 13% below the actual median, BMW X5 2020 about 2x). Handled in the product by abstention (journal 36: no forecast when close sales of the same model ±2 years disagree with P50 or are too few for an expensive car); the model itself is not fixed yet.
- Price drift after 2022 (sanctions, utilization fee): handled by the log target, a date feature and time-based validation.

## Known pitfalls (must be handled)

- **Leakage from the future:** for every feature ask whether it is known before the auction starts.
- **Same vehicle in train and test:** only sold trades are collected, so a car usually appears once; resales are found by VIN hash and removed. Time split handles the rest.
- **Time split**, not random split.
- **Comparables:** for a test lot, show only lots sold before it.
- **Rare makes / regions / vehicle types:** regularize, merge rare categories.
- **Dirty prices:** typos, thousands vs rubles → outlier cleaning.
- Use sklearn Pipeline / fit preprocessing on train only.

## Models and product

- Models: baseline (median of comparables), linear quantile regression, CatBoost MultiQuantile, ensemble of the last two (current). Two modes: without the start price and with the first-auction start price; the web/API picks the mode by whether the manager filled the start price field.
- Lot text: regex extraction (`src/features/text.py`) + normalization; TF-IDF and a local LLM (Qwen3 8B) were tested and add nothing over regex.
- Explanations: factors in % from the linear model (`explain.py`, additive in log space), not SHAP. Comparables: same make + model (then make), ranked by defect flags, year gap, recency, only lots sold before the date (`comparables.py`).
- Web UI in `web/` (also needed for a separate web course): paste the lot text → `/api/extract` prefills the form → manager checks → `/api/predict` returns quartiles, corridor, factors, comparables, market links. Form fields and flags match `docs/labeling_guide.md`; make, model, year required, the rest optional ("не указано"). FastAPI `src/api/app.py` (2026-10-17) serves the page, `/api/extract` and the pilot journal (JSON file, blind estimate + forecast + outcome, `web/pilot.html` compares manager vs model); `/api/predict` answers from the saved models in `models/` (demo mode only if they are missing). Result screen: typical start + price ladder with P(sold at the first auction), two outcomes with typical time to sale (first auction 1.5-2 months, otherwise 4-6 months, 2025 data), sale corridor, printable report (print CSS), collapsed basis.

## Data collection plan (design doc 2.2)

- ЕФРСБ is protected by Qrator (403 even for a real automated browser); official API is paid. Not used, no bypass attempts.
- Main source: ЭТП ЦДТ (torgi.cdtrf.ru). Open JSON API without auth: `/api/Trade/trades?SignContract=true&Categories=1&PageSize=..&PageNum=..` (status flags by enumName: SignContract = sold with contract, Complete, NotHeld...; Categories: 1 passenger, 2 truck/commercial, 4 buses). Catalogs at `/api/Catalog/*`. robots.txt empty.
- Archive since Feb 2020; sold: 26,164 passenger, 4,680 truck/commercial (Oct 2026).
- List price is NOT final (equals start price). Lot card `/trades/{tradeId}` is HTML (SSR): description, start price, price-drop schedule with bid counts, final price ("Итоговая цена"), result date, protocols. Card data is taken from the Nuxt `__NUXT_DATA__` JSON embedded in the HTML; `/api/Trade/{id}` needs auth.
- Personal data at parse time: debtor and winner fields are not kept; debtor INN, debtor name, lot title and manager INN only as hashes (`debtor_key`, `debtor_name_key`, `title_key`, `arbman_key`); in lot texts VIN (any case), plates, phones, names, INN, СНИЛС and apartment numbers are masked (some names in free text may remain); from VIN only WMI, VDS (chars 4-8), the year code and a hash (`vin_hash`) are kept; from the case number only the court code. All-status catalog (`cdtrf_trades.parquet`) keeps no texts.
- Open: include company debtors or only individuals; other platforms (РАД) postponed.
- МЭТС (m-ets.ru) checked 2026-10-15 and dropped for now: car cards have structured fields (make, model, year, power, mileage, drive, gearbox) and final/contract price, but no API; robots.txt disallows everything except lot cards and sitemaps (search, catalog, pagination forbidden); sitemaps have no category → ~110k completed lots since 2024 to download for ~5% cars (~3k sold), ~24 h. Geo-blocks non-Russian IPs (needs split tunneling = user's real IP). Decision: work without МЭТС; do not bypass robots.txt. Revisit only if mileage proves critical (options: sample via sitemap, ask МЭТС for an export, user filters search manually).
- Related work: Жучкова С. (HSE, 2020), ranking of profitable car lots for buyers, manual feature extraction from text, platforms ЦДТ, МЭТС, НИС, РАД, Купецъ.

## Current state (snapshot 2026-10-16; history in `journal/JOURNAL.md`, experiments 01-24)

- Data: 23,244 sold passenger cards since 2022 on disk (`data/raw/cdtrf/cards`), all-status catalog of 72k trades since 2022 for stage linking. Dataset = lots published since 2023-01-01 (`SINCE` in `build.py`), 17,685 lots after cleaning (censoring of the last 3 months, VIN relistings and relistings without VIN, shares, commercial, trailers, price typos). 2022 tested and not used (journal 23).
- Validation: split by `requestTimeBegin`; expanding-window CV on 2023-2025, 4 folds = 2025 quarters; a fold trains only on lots sold before its start (`sold_at`); 2026 is the final test, run once on 2026-10-17 for all three models (journal 35, quarters 2026Q1-Q3 with the CV scheme): model 1 26.7% / with start 21.1%, model 2 24.0%, model 3 log loss 0.329 / AUC 0.770 / ECE 0.009, all at the CV level.
- Current CV (journal 23 rerun): baseline MdAPE 36.0%; ensemble without start 26.5% / tail (>50% error) 25.7% / coverage 50.7% / pinball 0.173; with start 21.8% / 19.4% / 50.2% / 0.140. Linear: alpha 3e-5, min_frequency 2, month trend = piecewise-linear spline with 1 kink; CatBoost: depth 4, l2 10, 1500 it., CTR `Borders:TargetBorderCount=15`; corridor `WIDTH_K` 1.12 / 1.15.
- Key findings for the defense: the model is information-limited (identical make+model+year in one quarter vary with leave-one-out MdAPE 22-23% even with equal defect flags and sale stage; mileage is in 2.6% of texts; journal 24); the start price explains 44% of the error variance (the manager saw the car); the last ~10 experiments moved metrics by ±0.3 pp, so further model tuning is not worth it on this data (24: CatBoost on the discount target, no change). Pilot comparison must use the manager's blind estimate of the sale price, not the start price (the start is a market-value valuation by law, not a sale forecast).
- Extraction quality (test2 holdout): make 0.96, model 0.93, year / power / engine 1.00; flags P/R ≈ 0.7-1.0. Gold set `labels/gold.csv` 587 lots (dev2 + flags = tuning splits, test2 = holdout). User still has to verify a sample of 30-40 Claude labels.
- Weak spots: CV is optimistic (~20 decisions on the same folds); start model: 19% of training lots use the 0.9 fallback, bimodal price on lots sold at the first auction; trend extrapolation may lag a market turn; selection bias (sold lots only); `notebooks/02_eda_full.ipynb` is computed on old data.
- Repo: git history squashed 2026-10-16 (backup branch `backup/before-squash`); last edits (journal 23, docs) may be uncommitted; scratch scripts in `misc/scratch_2026-10-16/`.
- First auctions dataset: `data/processed/first_auctions.parquet` (`src.dataset.first_auction`), 26.7k first auctions 2023-2026 from the all-status catalog (`stages.first_auctions`) with their own cards (21.9k collected into `data/raw/cdtrf/cards_first/`); sold-at-first share fell 36% (2023) → 24% (2024) → 14% (2025).
- Model 2 (journal 25, 28, `src/models/typical_start.py`): typical first-auction start, trained and checked on all first auctions: MdAPE 24.4% / tail 22.7% / coverage 51.0% / pinball 0.155; noise ceiling of starts for identical cars 24-25%.
- Model 3 (journal 26, 27, `src/models/first_sale.py`): P(sold at the first auction), logistic (C 0.1) + CatBoost (300 it., monotone in price) averaged, market estimate = model 1 ensemble P25/P50/P75 (ratio of the start to P50 + corridor width): log loss 0.355 / Brier 0.107 / AUC 0.766, calibration ECE 0.010 (base-rate baseline 0.424); sold immediately 48% when the start is a third below the market estimate, 4.5% when it is ~2x above. Plateau reached (journal 27, 29-34): settings, recalibration, label cleaning, supply, ratio to the typical start, boosting from the logistic do not help; its ceiling is the accuracy of model 1.
- Next (main line, 2026-10-17): (1) done: B14, B15; (2) done: B10 (models 3, journal 26) first-auction sale probability (label from the catalog, monotone in price, calibration; train only on first auctions finished before the fold start); (3) done: 2026 test (journal 35); (4) done: models trained on all data in `models/` (`src.models.train_final`), `/api/predict` live (`src/models/serve.py`); (5) pilot with the brother (blind estimates, check first-auction sale rate against predicted p); (6) defense materials.
